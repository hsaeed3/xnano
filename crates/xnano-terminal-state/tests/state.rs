use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};

use serde_json::json;
use xnano_terminal_state::{
    Error, Listener, Node, Patch, Schema, Store,
    store::{Change, ListenerFailure},
};

fn node(value: serde_json::Value) -> Node {
    Node::from_json(&value).unwrap()
}

fn path(tokens: &[&str]) -> Vec<String> {
    tokens.iter().map(|token| (*token).to_owned()).collect()
}

fn world_schema() -> Schema {
    Schema::compile(
        &json!({
            "type": "object",
            "properties": {
                "player": {
                    "type": "object",
                    "properties": {
                        "health": {"type": "integer", "minimum": 0, "maximum": 100},
                        "name": {"type": "string", "minLength": 1},
                    },
                    "required": ["health", "name"],
                    "additionalProperties": false,
                },
                "items": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
                "score": {"type": "number"},
            },
            "required": ["player"],
        }),
        64,
    )
    .unwrap()
}

fn world() -> Arc<Store> {
    Store::new(
        node(json!({"player": {"health": 10, "name": "Ada"}, "items": ["rope"], "score": 1.5})),
        world_schema(),
    )
    .unwrap()
}

#[test]
fn schema_reports_every_problem_with_a_path() {
    let schema = world_schema();
    let error = schema
        .validate(&node(
            json!({"player": {"health": 500, "name": ""}, "items": [1]}),
        ))
        .unwrap_err();
    let Error::Validation(issues) = error else {
        panic!("expected validation issues")
    };
    let constraints: Vec<_> = issues
        .iter()
        .map(|issue| issue.constraint.as_str())
        .collect();
    assert!(constraints.contains(&"maximum"));
    assert!(constraints.contains(&"minLength"));
    assert!(constraints.contains(&"type"));
    assert!(
        issues
            .iter()
            .any(|issue| issue.path == path(&["player", "health"]))
    );
}

#[test]
fn unsupported_keywords_fail_compilation() {
    let error = Schema::compile(&json!({"if": {"type": "string"}}), 8).unwrap_err();
    assert!(error.to_string().contains("\"if\""), "{error}");
}

#[test]
fn integers_are_never_coerced() {
    let schema = Schema::compile(&json!({"type": "integer"}), 8).unwrap();
    assert!(schema.validate(&node(json!(3))).is_ok());
    assert!(schema.validate(&node(json!(3.0))).is_err());
}

#[test]
fn references_resolve_and_recursion_terminates() {
    let schema = Schema::compile(
        &json!({
            "$defs": {"tree": {"type": "object", "properties": {
                "children": {"type": "array", "items": {"$ref": "#/$defs/tree"}}}}},
            "$ref": "#/$defs/tree",
        }),
        32,
    )
    .unwrap();
    assert!(
        schema
            .validate(&node(json!({"children": [{"children": []}]})))
            .is_ok()
    );
    assert!(
        schema
            .validate(&node(json!({"children": [{"children": 3}]})))
            .is_err()
    );
}

#[test]
fn schema_at_follows_properties_and_items() {
    let schema = world_schema();
    let health = schema.at(&path(&["player", "health"])).unwrap();
    assert_eq!(health.to_json()["maximum"], 100);
    let item = schema.at(&path(&["items", "0"])).unwrap();
    assert_eq!(item.to_json()["type"], "string");
    assert!(schema.at(&path(&["player", "mana"])).is_err());
}

#[test]
fn patches_follow_rfc_6902() {
    let root = node(json!({"a": [1, 2], "b": {"c": 1}}));
    let patch = Patch::from_json(&json!([
        {"op": "add", "path": "/a/1", "value": 9},
        {"op": "add", "path": "/a/-", "value": 3},
        {"op": "replace", "path": "/b/c", "value": 2},
        {"op": "copy", "from": "/b", "path": "/d"},
        {"op": "move", "from": "/a/0", "path": "/e"},
        {"op": "test", "path": "/e", "value": 1},
        {"op": "remove", "path": "/b"},
    ]))
    .unwrap();
    let updated = patch.apply(&root).unwrap();
    assert_eq!(
        updated.to_json(),
        json!({"a": [9, 2, 3], "d": {"c": 2}, "e": 1})
    );
    assert_eq!(Patch::from_json(&patch.to_json()).unwrap(), patch);
}

#[test]
fn a_failed_test_aborts_the_whole_patch() {
    let root = node(json!({"a": 1}));
    let patch = Patch::from_json(&json!([
        {"op": "replace", "path": "/a", "value": 2},
        {"op": "test", "path": "/a", "value": 3},
    ]))
    .unwrap();
    assert!(patch.apply(&root).is_err());
    assert_eq!(root.to_json(), json!({"a": 1}));
}

#[test]
fn malformed_patches_explain_themselves() {
    let error = Patch::from_json(&json!([{"op": "bump", "path": "/a"}])).unwrap_err();
    assert!(
        error.to_string().contains("add, remove, replace"),
        "{error}"
    );
    let error = Patch::from_json(&json!([{"op": "add", "path": "a", "value": 1}])).unwrap_err();
    assert!(error.to_string().contains("JSON Pointer"), "{error}");
}

#[test]
fn commits_validate_atomically_and_bump_revisions() {
    let store = world();
    assert_eq!(store.revision(), 0);
    let change = store
        .set(&path(&["player", "health"]), node(json!(7)), None)
        .unwrap()
        .unwrap();
    assert_eq!((change.before_revision, change.revision), (0, 1));
    let rejected = store.set(&path(&["player", "health"]), node(json!(-1)), None);
    assert!(matches!(rejected, Err(Error::Validation(_))));
    assert_eq!(store.revision(), 1);
    assert_eq!(
        store
            .snapshot(&path(&["player", "health"]))
            .unwrap()
            .node
            .to_json(),
        json!(7)
    );
}

#[test]
fn no_op_commits_publish_nothing() {
    let store = world();
    let change = store
        .set(&path(&["player", "health"]), node(json!(10)), None)
        .unwrap();
    assert!(change.is_none());
    assert_eq!(store.revision(), 0);
}

#[test]
fn expected_revisions_detect_conflicts() {
    let store = world();
    store
        .set(&path(&["score"]), node(json!(2.5)), None)
        .unwrap();
    let error = store
        .set(&path(&["score"]), node(json!(3.5)), Some(0))
        .unwrap_err();
    assert_eq!(
        error,
        Error::Conflict {
            expected: 0,
            actual: 1
        }
    );
}

#[test]
fn branch_revisions_track_only_their_branch() {
    let store = world();
    store
        .set(&path(&["score"]), node(json!(9.0)), None)
        .unwrap();
    assert_eq!(store.revision_at(&path(&["score"])), 1);
    assert_eq!(store.revision_at(&path(&["player", "health"])), 0);
    store
        .set(
            &path(&["player"]),
            node(json!({"health": 1, "name": "Bo"})),
            None,
        )
        .unwrap();
    assert_eq!(store.revision_at(&path(&["player", "health"])), 2);
    assert_eq!(store.revision_at(&[]), 2);
}

#[test]
fn transactions_validate_the_combined_candidate() {
    let store = world();
    let mut transaction = store.transaction(None);
    transaction
        .set(&path(&["player", "health"]), node(json!(0)))
        .unwrap();
    transaction
        .set(&path(&["player", "name"]), node(json!("Bo")))
        .unwrap();
    assert_eq!(
        transaction
            .snapshot()
            .node
            .get(&path(&["player", "name"]))
            .unwrap()
            .to_json(),
        json!("Bo")
    );
    assert_eq!(store.revision(), 0, "staged edits are isolated");
    let change = transaction.commit().unwrap().unwrap();
    assert_eq!(change.revision, 1);
    assert_eq!(change.paths.len(), 2);
}

#[test]
fn transaction_rollback_publishes_nothing() {
    let store = world();
    let mut transaction = store.transaction(None);
    transaction
        .set(&path(&["score"]), node(json!(5.5)))
        .unwrap();
    transaction.rollback();
    assert!(transaction.commit().is_err());
    assert_eq!(store.revision(), 0);
}

#[test]
fn transactions_keep_unrelated_concurrent_changes() {
    let store = world();
    let mut transaction = store.transaction(None);
    transaction
        .set(&path(&["score"]), node(json!(4.5)))
        .unwrap();
    store
        .set(&path(&["player", "health"]), node(json!(3)), None)
        .unwrap();
    transaction.commit().unwrap();
    let root = store.snapshot(&[]).unwrap().node.to_json();
    assert_eq!(root["score"], 4.5);
    assert_eq!(root["player"]["health"], 3);
}

struct Counter(Arc<AtomicUsize>);

impl Listener for Counter {
    fn notify(&self, _: &Arc<Change>) -> Result<(), ListenerFailure> {
        self.0.fetch_add(1, Ordering::SeqCst);
        Ok(())
    }
}

#[test]
fn subscriptions_queue_until_drained() {
    let store = world();
    let seen = Arc::new(AtomicUsize::new(0));
    let handle = store.subscribe(
        vec![path(&["player"])],
        true,
        Arc::new(Counter(seen.clone())),
    );
    store
        .set(&path(&["score"]), node(json!(3.5)), None)
        .unwrap();
    store
        .set(&path(&["player", "health"]), node(json!(4)), None)
        .unwrap();
    assert_eq!(seen.load(Ordering::SeqCst), 0);
    assert_eq!(
        store.drain(10).ok(),
        Some(1),
        "only the player branch matches"
    );
    assert_eq!(seen.load(Ordering::SeqCst), 1);
    handle.cancel();
    store
        .set(&path(&["player", "health"]), node(json!(5)), None)
        .unwrap();
    assert_eq!(store.drain(10).ok(), Some(0));
}

#[test]
fn descendant_changes_can_be_excluded() {
    let store = world();
    let seen = Arc::new(AtomicUsize::new(0));
    store.subscribe(
        vec![path(&["items"])],
        false,
        Arc::new(Counter(seen.clone())),
    );
    store
        .set(&path(&["items", "0"]), node(json!("axe")), None)
        .unwrap();
    store.drain(10).ok();
    assert_eq!(
        seen.load(Ordering::SeqCst),
        0,
        "an item changed, not the list"
    );
    store
        .set(&path(&["items"]), node(json!(["axe", "map"])), None)
        .unwrap();
    store.drain(10).ok();
    assert_eq!(
        seen.load(Ordering::SeqCst),
        1,
        "the list itself changed length"
    );
}

#[test]
fn wakers_fire_after_each_commit() {
    let store = world();
    let woke = Arc::new(AtomicUsize::new(0));
    let counter = woke.clone();
    store.attach_waker(Arc::new(move || {
        counter.fetch_add(1, Ordering::SeqCst);
    }));
    store
        .set(&path(&["score"]), node(json!(7.5)), None)
        .unwrap();
    store
        .set(&path(&["score"]), node(json!(7.5)), None)
        .unwrap();
    assert_eq!(
        woke.load(Ordering::SeqCst),
        1,
        "a no-op commit wakes nobody"
    );
}

#[test]
fn observations_enforce_grants_and_versions() {
    let store = world();
    let observation = store
        .observe(vec![path(&["player"])], vec![path(&["player", "health"])])
        .unwrap();
    assert_eq!(observation.selection.entries.len(), 1);

    let allowed =
        Patch::from_json(&json!([{"op": "replace", "path": "/player/health", "value": 2}]))
            .unwrap();
    store.validate_observed(&allowed, &observation).unwrap();

    let denied =
        Patch::from_json(&json!([{"op": "replace", "path": "/player/name", "value": "Z"}]))
            .unwrap();
    assert!(matches!(
        store.validate_observed(&denied, &observation),
        Err(Error::Access(_))
    ));

    let ancestor = Patch::from_json(&json!([
        {"op": "replace", "path": "/player", "value": {"health": 1, "name": "Z"}}
    ]))
    .unwrap();
    assert!(matches!(
        store.validate_observed(&ancestor, &observation),
        Err(Error::Access(_))
    ));

    store
        .set(&path(&["player", "health"]), node(json!(9)), None)
        .unwrap();
    assert!(matches!(
        store.apply_observed(&allowed, &observation),
        Err(Error::Conflict { .. })
    ));

    store
        .set(&path(&["score"]), node(json!(8.5)), None)
        .unwrap();
    let fresh = store
        .observe(vec![path(&["player"])], vec![path(&["player", "health"])])
        .unwrap();
    store
        .set(&path(&["score"]), node(json!(9.5)), None)
        .unwrap();
    assert!(
        store.apply_observed(&allowed, &fresh).unwrap().is_some(),
        "unrelated changes do not conflict"
    );
}

#[test]
fn observations_are_bound_to_their_store() {
    let first = world();
    let second = world();
    let observation = first.observe(vec![], vec![path(&["score"])]).unwrap();
    let patch =
        Patch::from_json(&json!([{"op": "replace", "path": "/score", "value": 1.5}])).unwrap();
    assert!(matches!(
        second.validate_observed(&patch, &observation),
        Err(Error::Access(_))
    ));
}
