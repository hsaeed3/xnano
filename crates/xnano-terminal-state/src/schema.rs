//! JSON Schema, compiled once and validated natively.
//!
//! The supported vocabulary is explicit. A keyword that is not supported fails
//! compilation instead of being silently ignored:
//!
//! - types and values: `type`, `enum`, `const`;
//! - numbers: `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `multipleOf`;
//! - strings: `minLength`, `maxLength`, `pattern`;
//! - arrays: `items`, `prefixItems`, `minItems`, `maxItems`, `uniqueItems`;
//! - objects: `properties`, `required`, `additionalProperties`, `patternProperties`,
//!   `propertyNames`, `minProperties`, `maxProperties`;
//! - combinators: `anyOf`, `oneOf`, `allOf`, `not`;
//! - references: `$ref` to a location in the same document, with `$defs` / `definitions`;
//! - annotations, which never affect validation: `title`, `description`, `default`,
//!   `examples`, `format`, `deprecated`, `readOnly`, `writeOnly`, `$schema`, `$id`,
//!   `$comment` and any `x-` extension;
//! - `x-xnano`, a semantic rule registered with [`register_semantic_rule`].
//!
//! Integers are never coerced: a schema of type `integer` accepts only integer values.

use std::collections::HashMap;
use std::sync::{Arc, OnceLock, RwLock};

use regex::Regex;
use serde_json::Value;

use crate::error::{Error, Issue};
use crate::node::{Node, parse_index, parse_pointer};

const MAXIMUM_ISSUES: usize = 64;

/// A semantic check for values that JSON Schema cannot express.
///
/// It receives the value and the `x-xnano` object of the schema, and returns the problems
/// it found as `(path below the value, message)` pairs.
pub type SemanticRule = Arc<dyn Fn(&Node, &Value) -> Vec<(Vec<String>, String)> + Send + Sync>;

fn rules() -> &'static RwLock<HashMap<String, SemanticRule>> {
    static RULES: OnceLock<RwLock<HashMap<String, SemanticRule>>> = OnceLock::new();
    RULES.get_or_init(|| RwLock::new(HashMap::new()))
}

/// Make `name` available to schemas as `{"x-xnano": {"rule": name, ...}}`.
pub fn register_semantic_rule(name: &str, rule: SemanticRule) {
    rules()
        .write()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
        .insert(name.to_owned(), rule);
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum Bound {
    Integer(i64),
    Float(f64),
}

impl Bound {
    fn from_json(value: &Value, keyword: &str) -> Result<Self, Error> {
        if let Some(integer) = value.as_i64() {
            Ok(Self::Integer(integer))
        } else if let Some(float) = value.as_f64() {
            Ok(Self::Float(float))
        } else {
            Err(compile_error(
                keyword,
                "must be a number, for example 0 or 1.5",
            ))
        }
    }

    fn compare(self, node: &Node) -> Option<std::cmp::Ordering> {
        match (node, self) {
            (Node::Integer(value), Self::Integer(bound)) => Some(value.cmp(&bound)),
            (Node::Integer(value), Self::Float(bound)) => (*value as f64).partial_cmp(&bound),
            (Node::Float(value), Self::Integer(bound)) => value.partial_cmp(&(bound as f64)),
            (Node::Float(value), Self::Float(bound)) => value.partial_cmp(&bound),
            _ => None,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum TypeName {
    Null,
    Boolean,
    Integer,
    Number,
    String,
    Array,
    Object,
}

impl TypeName {
    fn parse(name: &str) -> Result<Self, Error> {
        Ok(match name {
            "null" => Self::Null,
            "boolean" => Self::Boolean,
            "integer" => Self::Integer,
            "number" => Self::Number,
            "string" => Self::String,
            "array" => Self::Array,
            "object" => Self::Object,
            other => {
                return Err(compile_error(
                    "type",
                    &format!(
                        "\"{other}\" is not a JSON Schema type; use null, boolean, integer, \
                         number, string, array or object"
                    ),
                ));
            }
        })
    }

    fn accepts(self, node: &Node) -> bool {
        matches!(
            (self, node),
            (Self::Null, Node::Null)
                | (Self::Boolean, Node::Bool(_))
                | (Self::Integer, Node::Integer(_))
                | (Self::Number, Node::Integer(_) | Node::Float(_))
                | (Self::String, Node::String(_))
                | (Self::Array, Node::Array(_))
                | (Self::Object, Node::Object(_))
        )
    }

    fn label(self) -> &'static str {
        match self {
            Self::Null => "null",
            Self::Boolean => "boolean",
            Self::Integer => "integer",
            Self::Number => "number",
            Self::String => "string",
            Self::Array => "array",
            Self::Object => "object",
        }
    }
}

enum Additional {
    Allowed,
    Forbidden,
    Schema(usize),
}

struct SemanticCheck {
    name: String,
    arguments: Value,
    rule: SemanticRule,
}

#[derive(Default)]
struct Keywords {
    is_valid: Option<bool>,
    reference: Option<usize>,
    types: Vec<TypeName>,
    enumeration: Vec<Node>,
    constant: Option<Node>,
    minimum: Option<Bound>,
    maximum: Option<Bound>,
    exclusive_minimum: Option<Bound>,
    exclusive_maximum: Option<Bound>,
    multiple_of: Option<Bound>,
    minimum_length: Option<usize>,
    maximum_length: Option<usize>,
    pattern: Option<(String, Regex)>,
    items: Option<usize>,
    prefix_items: Vec<usize>,
    minimum_items: Option<usize>,
    maximum_items: Option<usize>,
    has_unique_items: bool,
    properties: Vec<(String, usize)>,
    required: Vec<String>,
    additional: Option<Additional>,
    pattern_properties: Vec<(Regex, usize)>,
    property_names: Option<usize>,
    minimum_properties: Option<usize>,
    maximum_properties: Option<usize>,
    any_of: Vec<usize>,
    one_of: Vec<usize>,
    all_of: Vec<usize>,
    not: Option<usize>,
    semantic: Option<SemanticCheck>,
}

struct SchemaNode {
    source: Arc<Value>,
    keywords: Keywords,
}

struct Arena {
    nodes: Vec<SchemaNode>,
    document: Value,
}

/// A compiled schema.
#[derive(Clone)]
pub struct Schema {
    arena: Arc<Arena>,
    root: usize,
}

impl std::fmt::Debug for Schema {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(formatter, "Schema({})", self.to_json())
    }
}

fn compile_error(keyword: &str, message: &str) -> Error {
    Error::validation(
        &[],
        "schema",
        format!("the schema keyword \"{keyword}\" {message}"),
    )
}

const ANNOTATIONS: &[&str] = &[
    "title",
    "description",
    "default",
    "examples",
    "format",
    "deprecated",
    "readOnly",
    "writeOnly",
    "$schema",
    "$id",
    "$comment",
    "$defs",
    "definitions",
];

struct Compiler<'a> {
    document: &'a Value,
    nodes: Vec<Option<SchemaNode>>,
    references: HashMap<String, usize>,
    maximum_depth: usize,
}

impl Compiler<'_> {
    fn allocate(&mut self) -> usize {
        self.nodes.push(None);
        self.nodes.len() - 1
    }

    fn compile(&mut self, schema: &Value, depth: usize) -> Result<usize, Error> {
        let index = self.allocate();
        self.compile_into(index, schema, depth)?;
        Ok(index)
    }

    fn reference(&mut self, reference: &str, depth: usize) -> Result<usize, Error> {
        if let Some(index) = self.references.get(reference) {
            return Ok(*index);
        }
        let Some(pointer) = reference.strip_prefix('#') else {
            return Err(compile_error(
                "$ref",
                &format!(
                    "\"{reference}\" points outside the schema document; only references that \
                     start with \"#\" are supported"
                ),
            ));
        };
        let tokens = parse_pointer(pointer).map_err(|_| {
            compile_error("$ref", &format!("\"{reference}\" is not a valid reference"))
        })?;
        let mut target = self.document;
        for token in &tokens {
            let next = match target {
                Value::Object(entries) => entries.get(token.as_str()),
                Value::Array(items) => parse_index(token).and_then(|index| items.get(index)),
                _ => None,
            };
            target = next.ok_or_else(|| {
                compile_error(
                    "$ref",
                    &format!("\"{reference}\" does not point at anything in the schema"),
                )
            })?;
        }
        let index = self.allocate();
        self.references.insert(reference.to_owned(), index);
        self.compile_into(index, target, depth)?;
        Ok(index)
    }

    fn compile_all(
        &mut self,
        value: &Value,
        keyword: &str,
        depth: usize,
    ) -> Result<Vec<usize>, Error> {
        let Value::Array(items) = value else {
            return Err(compile_error(keyword, "must be a list of schemas"));
        };
        if items.is_empty() {
            return Err(compile_error(keyword, "must not be empty"));
        }
        items
            .iter()
            .map(|item| self.compile(item, depth + 1))
            .collect()
    }

    fn count(value: &Value, keyword: &str) -> Result<usize, Error> {
        value
            .as_u64()
            .and_then(|count| usize::try_from(count).ok())
            .ok_or_else(|| compile_error(keyword, "must be a whole number that is zero or more"))
    }

    fn compile_into(&mut self, index: usize, schema: &Value, depth: usize) -> Result<(), Error> {
        if depth > self.maximum_depth {
            return Err(compile_error(
                "$ref",
                &format!(
                    "nests deeper than the maximum depth of {}; simplify the schema or raise \
                     maximum_depth",
                    self.maximum_depth
                ),
            ));
        }
        let mut keywords = Keywords::default();
        match schema {
            Value::Bool(flag) => keywords.is_valid = Some(*flag),
            Value::Object(entries) => {
                for (keyword, value) in entries {
                    self.compile_keyword(&mut keywords, keyword, value, depth)?;
                }
            }
            _ => {
                return Err(compile_error(
                    "schema",
                    "must be an object, or true or false",
                ));
            }
        }
        self.nodes[index] = Some(SchemaNode {
            source: Arc::new(schema.clone()),
            keywords,
        });
        Ok(())
    }

    fn compile_keyword(
        &mut self,
        keywords: &mut Keywords,
        keyword: &str,
        value: &Value,
        depth: usize,
    ) -> Result<(), Error> {
        match keyword {
            "$ref" => {
                let Value::String(reference) = value else {
                    return Err(compile_error("$ref", "must be a string"));
                };
                keywords.reference = Some(self.reference(reference, depth + 1)?);
            }
            "type" => {
                keywords.types = match value {
                    Value::String(name) => vec![TypeName::parse(name)?],
                    Value::Array(names) => names
                        .iter()
                        .map(|name| {
                            name.as_str()
                                .ok_or_else(|| compile_error("type", "must hold type names"))
                                .and_then(TypeName::parse)
                        })
                        .collect::<Result<_, _>>()?,
                    _ => return Err(compile_error("type", "must be a type name or a list")),
                };
            }
            "enum" => {
                let Value::Array(items) = value else {
                    return Err(compile_error("enum", "must be a list of values"));
                };
                keywords.enumeration = items
                    .iter()
                    .map(Node::from_json)
                    .collect::<Result<_, _>>()?;
            }
            "const" => keywords.constant = Some(Node::from_json(value)?),
            "minimum" => keywords.minimum = Some(Bound::from_json(value, keyword)?),
            "maximum" => keywords.maximum = Some(Bound::from_json(value, keyword)?),
            "exclusiveMinimum" => {
                keywords.exclusive_minimum = Some(Bound::from_json(value, keyword)?);
            }
            "exclusiveMaximum" => {
                keywords.exclusive_maximum = Some(Bound::from_json(value, keyword)?);
            }
            "multipleOf" => {
                let bound = Bound::from_json(value, keyword)?;
                if matches!(bound, Bound::Integer(0))
                    || matches!(bound, Bound::Float(float) if float <= 0.0)
                {
                    return Err(compile_error(keyword, "must be greater than zero"));
                }
                keywords.multiple_of = Some(bound);
            }
            "minLength" => keywords.minimum_length = Some(Self::count(value, keyword)?),
            "maxLength" => keywords.maximum_length = Some(Self::count(value, keyword)?),
            "pattern" => {
                let Value::String(pattern) = value else {
                    return Err(compile_error("pattern", "must be a string"));
                };
                let regex = Regex::new(pattern).map_err(|error| {
                    compile_error(
                        "pattern",
                        &format!("\"{pattern}\" is not a valid regular expression: {error}"),
                    )
                })?;
                keywords.pattern = Some((pattern.clone(), regex));
            }
            "items" => {
                if value.is_array() {
                    return Err(compile_error(
                        "items",
                        "must be one schema; use \"prefixItems\" for a list of positional schemas",
                    ));
                }
                keywords.items = Some(self.compile(value, depth + 1)?);
            }
            "prefixItems" => keywords.prefix_items = self.compile_all(value, keyword, depth)?,
            "minItems" => keywords.minimum_items = Some(Self::count(value, keyword)?),
            "maxItems" => keywords.maximum_items = Some(Self::count(value, keyword)?),
            "uniqueItems" => keywords.has_unique_items = value.as_bool().unwrap_or(false),
            "properties" => {
                let Value::Object(entries) = value else {
                    return Err(compile_error("properties", "must be an object of schemas"));
                };
                for (name, schema) in entries {
                    let compiled = self.compile(schema, depth + 1)?;
                    keywords.properties.push((name.clone(), compiled));
                }
            }
            "required" => {
                let Value::Array(names) = value else {
                    return Err(compile_error(
                        "required",
                        "must be a list of property names",
                    ));
                };
                keywords.required = names
                    .iter()
                    .map(|name| {
                        name.as_str()
                            .map(str::to_owned)
                            .ok_or_else(|| compile_error("required", "must hold property names"))
                    })
                    .collect::<Result<_, _>>()?;
            }
            "additionalProperties" => {
                keywords.additional = Some(match value {
                    Value::Bool(true) => Additional::Allowed,
                    Value::Bool(false) => Additional::Forbidden,
                    schema => Additional::Schema(self.compile(schema, depth + 1)?),
                });
            }
            "patternProperties" => {
                let Value::Object(entries) = value else {
                    return Err(compile_error(
                        "patternProperties",
                        "must be an object of schemas",
                    ));
                };
                for (pattern, schema) in entries {
                    let regex = Regex::new(pattern).map_err(|error| {
                        compile_error(
                            "patternProperties",
                            &format!("\"{pattern}\" is not a valid regular expression: {error}"),
                        )
                    })?;
                    let compiled = self.compile(schema, depth + 1)?;
                    keywords.pattern_properties.push((regex, compiled));
                }
            }
            "propertyNames" => keywords.property_names = Some(self.compile(value, depth + 1)?),
            "minProperties" => keywords.minimum_properties = Some(Self::count(value, keyword)?),
            "maxProperties" => keywords.maximum_properties = Some(Self::count(value, keyword)?),
            "anyOf" => keywords.any_of = self.compile_all(value, keyword, depth)?,
            "oneOf" => keywords.one_of = self.compile_all(value, keyword, depth)?,
            "allOf" => keywords.all_of = self.compile_all(value, keyword, depth)?,
            "not" => keywords.not = Some(self.compile(value, depth + 1)?),
            // Without a `rule`, `x-xnano` is descriptive metadata (for example the paths a view grants).
            "x-xnano" => {
                if value.get("rule").is_some() {
                    keywords.semantic = Some(compile_semantic(value)?);
                }
            }
            other if ANNOTATIONS.contains(&other) || other.starts_with("x-") => {}
            other => {
                return Err(compile_error(
                    other,
                    "is not supported by xnano state schemas; remove it, or express the rule \
                     with the supported keywords (type, enum, const, minimum, maximum, \
                     minLength, maxLength, pattern, items, properties, required, \
                     additionalProperties, anyOf, oneOf, allOf, not and $ref)",
                ));
            }
        }
        Ok(())
    }
}

fn compile_semantic(value: &Value) -> Result<SemanticCheck, Error> {
    let name = value
        .get("rule")
        .and_then(Value::as_str)
        .ok_or_else(|| compile_error("x-xnano", "must be an object with a \"rule\" name"))?;
    let rule = rules()
        .read()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
        .get(name)
        .cloned()
        .ok_or_else(|| {
            compile_error(
                "x-xnano",
                &format!("names the rule \"{name}\", which is not registered"),
            )
        })?;
    Ok(SemanticCheck {
        name: name.to_owned(),
        arguments: value.clone(),
        rule,
    })
}

impl Schema {
    /// Compile a JSON Schema document.
    pub fn compile(document: &Value, maximum_depth: usize) -> Result<Self, Error> {
        let mut compiler = Compiler {
            document,
            nodes: Vec::new(),
            references: HashMap::new(),
            maximum_depth,
        };
        // Node 0 is the schema that accepts everything.
        compiler.compile(&Value::Bool(true), 0)?;
        let root = compiler.compile(document, 0)?;
        let nodes = compiler
            .nodes
            .into_iter()
            .map(|node| node.expect("every allocated schema node is compiled"))
            .collect();
        Ok(Self {
            arena: Arc::new(Arena {
                nodes,
                document: document.clone(),
            }),
            root,
        })
    }

    /// A schema that accepts every value.
    pub fn permissive() -> Self {
        Self::compile(&Value::Bool(true), 4).expect("the permissive schema compiles")
    }

    /// The JSON Schema this was compiled from.
    pub fn to_json(&self) -> Value {
        let source = (*self.arena.nodes[self.root].source).clone();
        if self.root != 1 && source.to_string().contains("\"$ref\"") {
            let mut combined = match source {
                Value::Object(entries) => entries,
                other => {
                    let mut entries = serde_json::Map::new();
                    entries.insert("allOf".into(), Value::Array(vec![other]));
                    entries
                }
            };
            for key in ["$defs", "definitions"] {
                if let Some(definitions) = self.arena.document.get(key) {
                    combined.entry(key).or_insert_with(|| definitions.clone());
                }
            }
            return Value::Object(combined);
        }
        source
    }

    /// Whether two handles share the same compiled schema.
    pub fn is_same(&self, other: &Self) -> bool {
        Arc::ptr_eq(&self.arena, &other.arena) && self.root == other.root
    }

    fn resolve(&self, mut index: usize) -> usize {
        // A reference to a reference is followed to the schema that carries keywords.
        for _ in 0..64 {
            match self.arena.nodes[index].keywords.reference {
                Some(target) => index = target,
                None => break,
            }
        }
        index
    }

    /// Validate `value`, reporting every problem found (up to a limit).
    pub fn validate(&self, value: &Node) -> Result<(), Error> {
        let mut issues = Vec::new();
        self.check(self.root, value, &mut Vec::new(), &mut issues, 0);
        if issues.is_empty() {
            Ok(())
        } else {
            Err(Error::Validation(issues))
        }
    }

    /// The schema for the branch at `path`.
    pub fn at(&self, path: &[String]) -> Result<Schema, Error> {
        let mut current = self.root;
        for (position, token) in path.iter().enumerate() {
            current = self.child(current, token).ok_or_else(|| {
                Error::validation(
                    &path[..=position],
                    "path",
                    format!(
                        "the schema does not allow \"{token}\" here; check the path against \
                         the schema's properties"
                    ),
                )
            })?;
        }
        Ok(Schema {
            arena: Arc::clone(&self.arena),
            root: current,
        })
    }

    fn child(&self, index: usize, token: &str) -> Option<usize> {
        let index = self.resolve(index);
        let keywords = &self.arena.nodes[index].keywords;
        if keywords.is_valid == Some(true) {
            return Some(0);
        }
        if let Some((_, schema)) = keywords.properties.iter().find(|(name, _)| name == token) {
            return Some(*schema);
        }
        if let Some((_, schema)) = keywords
            .pattern_properties
            .iter()
            .find(|(pattern, _)| pattern.is_match(token))
        {
            return Some(*schema);
        }
        if let Some(position) = parse_index(token)
            && let Some(schema) = keywords.prefix_items.get(position)
        {
            return Some(*schema);
        }
        if let Some(schema) = keywords.items {
            return Some(schema);
        }
        match &keywords.additional {
            Some(Additional::Schema(schema)) => return Some(*schema),
            Some(Additional::Forbidden) => {}
            Some(Additional::Allowed) => return Some(0),
            None => {
                let is_container = keywords.properties.is_empty()
                    && keywords.pattern_properties.is_empty()
                    && keywords.items.is_none()
                    && keywords.prefix_items.is_empty();
                if is_container
                    && keywords.all_of.is_empty()
                    && keywords.any_of.is_empty()
                    && keywords.one_of.is_empty()
                {
                    return Some(0);
                }
            }
        }
        for member in &keywords.all_of {
            if let Some(found) = self.child(*member, token) {
                return Some(found);
            }
        }
        let mut found = None;
        let mut count = 0;
        for member in keywords.any_of.iter().chain(&keywords.one_of) {
            if let Some(candidate) = self.child(*member, token) {
                found = Some(candidate);
                count += 1;
            }
        }
        match count {
            0 => None,
            1 => found,
            _ => Some(0),
        }
    }

    fn check(
        &self,
        index: usize,
        value: &Node,
        path: &mut Vec<String>,
        issues: &mut Vec<Issue>,
        depth: usize,
    ) {
        if issues.len() >= MAXIMUM_ISSUES {
            return;
        }
        if depth > 256 {
            issues.push(Issue::new(
                path,
                "depth",
                "the value nests deeper than 256 levels",
            ));
            return;
        }
        let keywords = &self.arena.nodes[index].keywords;
        match keywords.is_valid {
            Some(true) => return,
            Some(false) => {
                issues.push(Issue::new(path, "false", "no value is allowed here"));
                return;
            }
            None => {}
        }
        if let Some(target) = keywords.reference {
            self.check(target, value, path, issues, depth + 1);
        }
        self.check_values(keywords, value, path, issues);
        self.check_numbers(keywords, value, path, issues);
        self.check_strings(keywords, value, path, issues);
        self.check_arrays(keywords, value, path, issues, depth);
        self.check_objects(keywords, value, path, issues, depth);
        self.check_combinators(keywords, value, path, issues, depth);
        if let Some(check) = &keywords.semantic {
            for (relative, message) in (check.rule)(value, &check.arguments) {
                let mut full = path.clone();
                full.extend(relative);
                issues.push(Issue::new(
                    &full,
                    format!("x-xnano:{}", check.name),
                    message,
                ));
            }
        }
    }

    fn check_values(
        &self,
        keywords: &Keywords,
        value: &Node,
        path: &[String],
        issues: &mut Vec<Issue>,
    ) {
        if !keywords.types.is_empty() && !keywords.types.iter().any(|name| name.accepts(value)) {
            let expected: Vec<_> = keywords.types.iter().map(|name| name.label()).collect();
            issues.push(Issue::new(
                path,
                "type",
                format!(
                    "expected {} but found {}",
                    expected.join(" or "),
                    value.type_name()
                ),
            ));
        }
        if !keywords.enumeration.is_empty() && !keywords.enumeration.contains(value) {
            let allowed: Vec<_> = keywords
                .enumeration
                .iter()
                .map(|item| item.to_json().to_string())
                .collect();
            issues.push(Issue::new(
                path,
                "enum",
                format!(
                    "{} is not one of the allowed values: {}",
                    value.to_json(),
                    allowed.join(", ")
                ),
            ));
        }
        if let Some(constant) = &keywords.constant
            && constant != value
        {
            issues.push(Issue::new(
                path,
                "const",
                format!("the value must be exactly {}", constant.to_json()),
            ));
        }
    }

    fn check_numbers(
        &self,
        keywords: &Keywords,
        value: &Node,
        path: &[String],
        issues: &mut Vec<Issue>,
    ) {
        use std::cmp::Ordering;
        if !matches!(value, Node::Integer(_) | Node::Float(_)) {
            return;
        }
        let shown = value.to_json();
        let bounds: [(Option<Bound>, &str, &[Ordering], &str); 4] = [
            (
                keywords.minimum,
                "minimum",
                &[Ordering::Greater, Ordering::Equal],
                "at least",
            ),
            (
                keywords.maximum,
                "maximum",
                &[Ordering::Less, Ordering::Equal],
                "at most",
            ),
            (
                keywords.exclusive_minimum,
                "exclusiveMinimum",
                &[Ordering::Greater],
                "greater than",
            ),
            (
                keywords.exclusive_maximum,
                "exclusiveMaximum",
                &[Ordering::Less],
                "less than",
            ),
        ];
        for (bound, keyword, allowed, words) in bounds {
            if let Some(bound) = bound
                && !bound
                    .compare(value)
                    .is_some_and(|ordering| allowed.contains(&ordering))
            {
                let limit = match bound {
                    Bound::Integer(integer) => integer.to_string(),
                    Bound::Float(float) => float.to_string(),
                };
                issues.push(Issue::new(
                    path,
                    keyword,
                    format!("{shown} must be {words} {limit}"),
                ));
            }
        }
        if let Some(step) = keywords.multiple_of {
            let is_multiple = match (value, step) {
                (Node::Integer(number), Bound::Integer(step)) => number % step == 0,
                (_, step) => {
                    let number = match value {
                        Node::Integer(integer) => *integer as f64,
                        Node::Float(float) => *float,
                        _ => 0.0,
                    };
                    let step = match step {
                        Bound::Integer(integer) => integer as f64,
                        Bound::Float(float) => float,
                    };
                    let ratio = number / step;
                    (ratio - ratio.round()).abs() < 1e-9
                }
            };
            if !is_multiple {
                issues.push(Issue::new(
                    path,
                    "multipleOf",
                    format!("{shown} must be a multiple of the step"),
                ));
            }
        }
    }

    fn check_strings(
        &self,
        keywords: &Keywords,
        value: &Node,
        path: &[String],
        issues: &mut Vec<Issue>,
    ) {
        let Node::String(text) = value else {
            return;
        };
        let length = text.chars().count();
        if let Some(minimum) = keywords.minimum_length
            && length < minimum
        {
            issues.push(Issue::new(
                path,
                "minLength",
                format!("the text has {length} characters but needs at least {minimum}"),
            ));
        }
        if let Some(maximum) = keywords.maximum_length
            && length > maximum
        {
            issues.push(Issue::new(
                path,
                "maxLength",
                format!("the text has {length} characters but at most {maximum} are allowed"),
            ));
        }
        if let Some((pattern, regex)) = &keywords.pattern
            && !regex.is_match(text)
        {
            issues.push(Issue::new(
                path,
                "pattern",
                format!("the text does not match the pattern \"{pattern}\""),
            ));
        }
    }

    fn check_arrays(
        &self,
        keywords: &Keywords,
        value: &Node,
        path: &mut Vec<String>,
        issues: &mut Vec<Issue>,
        depth: usize,
    ) {
        let Node::Array(items) = value else {
            return;
        };
        if let Some(minimum) = keywords.minimum_items
            && items.len() < minimum
        {
            issues.push(Issue::new(
                path,
                "minItems",
                format!(
                    "the list has {} items but needs at least {minimum}",
                    items.len()
                ),
            ));
        }
        if let Some(maximum) = keywords.maximum_items
            && items.len() > maximum
        {
            issues.push(Issue::new(
                path,
                "maxItems",
                format!(
                    "the list has {} items but at most {maximum} are allowed",
                    items.len()
                ),
            ));
        }
        if keywords.has_unique_items {
            'search: for (position, item) in items.iter().enumerate() {
                for other in &items[..position] {
                    if other == item {
                        issues.push(Issue::new(
                            path,
                            "uniqueItems",
                            format!("the item at index {position} repeats an earlier item"),
                        ));
                        break 'search;
                    }
                }
            }
        }
        for (position, item) in items.iter().enumerate() {
            let schema = keywords
                .prefix_items
                .get(position)
                .copied()
                .or(keywords.items);
            if let Some(schema) = schema {
                path.push(position.to_string());
                self.check(schema, item, path, issues, depth + 1);
                path.pop();
            }
        }
    }

    fn check_objects(
        &self,
        keywords: &Keywords,
        value: &Node,
        path: &mut Vec<String>,
        issues: &mut Vec<Issue>,
        depth: usize,
    ) {
        let Node::Object(entries) = value else {
            return;
        };
        for name in &keywords.required {
            if !entries.contains_key(name.as_str()) {
                issues.push(Issue::new(
                    path,
                    "required",
                    format!("the required property \"{name}\" is missing"),
                ));
            }
        }
        if let Some(minimum) = keywords.minimum_properties
            && entries.len() < minimum
        {
            issues.push(Issue::new(
                path,
                "minProperties",
                format!(
                    "the object has {} properties but needs at least {minimum}",
                    entries.len()
                ),
            ));
        }
        if let Some(maximum) = keywords.maximum_properties
            && entries.len() > maximum
        {
            issues.push(Issue::new(
                path,
                "maxProperties",
                format!(
                    "the object has {} properties but at most {maximum} are allowed",
                    entries.len()
                ),
            ));
        }
        for (key, item) in entries.iter() {
            let mut schemas = Vec::new();
            let mut is_known = false;
            if let Some((_, schema)) = keywords
                .properties
                .iter()
                .find(|(name, _)| name.as_str() == &**key)
            {
                schemas.push(*schema);
                is_known = true;
            }
            for (pattern, schema) in &keywords.pattern_properties {
                if pattern.is_match(key) {
                    schemas.push(*schema);
                    is_known = true;
                }
            }
            if !is_known {
                match &keywords.additional {
                    Some(Additional::Forbidden) => {
                        issues.push(Issue::new(
                            path,
                            "additionalProperties",
                            format!("the property \"{key}\" is not allowed here"),
                        ));
                    }
                    Some(Additional::Schema(schema)) => schemas.push(*schema),
                    _ => {}
                }
            }
            if let Some(names) = keywords.property_names {
                self.check(names, &Node::string(key), path, issues, depth + 1);
            }
            for schema in schemas {
                path.push(key.to_string());
                self.check(schema, item, path, issues, depth + 1);
                path.pop();
            }
        }
    }

    fn check_combinators(
        &self,
        keywords: &Keywords,
        value: &Node,
        path: &mut Vec<String>,
        issues: &mut Vec<Issue>,
        depth: usize,
    ) {
        let branch_passes = |schema: usize, path: &mut Vec<String>| {
            let mut branch_issues = Vec::new();
            self.check(schema, value, path, &mut branch_issues, depth + 1);
            branch_issues
        };
        for member in &keywords.all_of {
            self.check(*member, value, path, issues, depth + 1);
        }
        if !keywords.any_of.is_empty() {
            let mut best: Option<Vec<Issue>> = None;
            let mut is_valid = false;
            for member in &keywords.any_of {
                let found = branch_passes(*member, path);
                if found.is_empty() {
                    is_valid = true;
                    break;
                }
                if best
                    .as_ref()
                    .is_none_or(|current| found.len() < current.len())
                {
                    best = Some(found);
                }
            }
            if !is_valid {
                issues.push(Issue::new(
                    path,
                    "anyOf",
                    format!(
                        "the value matches none of the {} allowed shapes; closest: {}",
                        keywords.any_of.len(),
                        best.and_then(|found| found.into_iter().next())
                            .map_or_else(String::new, |issue| issue.message)
                    ),
                ));
            }
        }
        if !keywords.one_of.is_empty() {
            let matches = keywords
                .one_of
                .iter()
                .filter(|member| branch_passes(**member, path).is_empty())
                .count();
            if matches != 1 {
                issues.push(Issue::new(
                    path,
                    "oneOf",
                    format!(
                        "the value matches {matches} of the {} allowed shapes but must match exactly one",
                        keywords.one_of.len()
                    ),
                ));
            }
        }
        if let Some(member) = keywords.not
            && branch_passes(member, path).is_empty()
        {
            issues.push(Issue::new(
                path,
                "not",
                "the value matches a shape that is not allowed",
            ));
        }
    }
}
