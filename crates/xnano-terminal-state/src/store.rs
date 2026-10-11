//! The state store: atomic, validated, revisioned commits with notifications.

use std::any::Any;
use std::collections::{HashMap, VecDeque};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex, MutexGuard, Weak};

use serde_json::Value;

use crate::error::Error;
use crate::node::{Node, Segment, to_pointer};
use crate::patch::{Patch, PatchOperation};
use crate::schema::Schema;

static NEXT_STORE_ID: AtomicU64 = AtomicU64::new(1);

fn lock<T>(mutex: &Mutex<T>) -> MutexGuard<'_, T> {
    mutex
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
}

/// A failure raised by a [`Listener`], carried back to whoever drained the queue.
pub struct ListenerFailure(pub Box<dyn Any + Send>);

/// Something told about each committed [`Change`], when the queue is drained.
pub trait Listener: Send + Sync {
    fn notify(&self, change: &Arc<Change>) -> Result<(), ListenerFailure>;
}

/// An immutable view of one branch at one revision.
#[derive(Debug, Clone)]
pub struct Snapshot {
    pub revision: u64,
    pub node: Node,
    pub schema: Schema,
}

impl Snapshot {
    /// The sub-branch at `path`.
    pub fn at(&self, path: &[String]) -> Result<Snapshot, Error> {
        let node = self.node.get(path).ok_or_else(|| {
            Error::validation(
                path,
                "path",
                format!(
                    "there is nothing at {}; check the path exists before reading it",
                    to_pointer(path)
                ),
            )
        })?;
        Ok(Snapshot {
            revision: self.revision,
            node: node.clone(),
            schema: self
                .schema
                .at(path)
                .unwrap_or_else(|_| Schema::permissive()),
        })
    }

    pub fn exists(&self, path: &[String]) -> bool {
        self.node.get(path).is_some()
    }

    /// Sparse values at several paths from this one revision. Missing paths are omitted.
    pub fn select(&self, paths: &[Vec<String>]) -> Selection {
        Selection {
            revision: self.revision,
            entries: paths
                .iter()
                .filter_map(|path| self.node.get(path).map(|node| (path.clone(), node.clone())))
                .collect(),
        }
    }
}

/// Values at several paths, all read from the same revision.
#[derive(Debug, Clone)]
pub struct Selection {
    pub revision: u64,
    pub entries: Vec<(Vec<String>, Node)>,
}

/// One published commit.
#[derive(Debug)]
pub struct Change {
    pub before_revision: u64,
    pub revision: u64,
    pub paths: Vec<Vec<Segment>>,
    pub patch: Patch,
    pub before: Snapshot,
    pub after: Snapshot,
}

#[derive(Default)]
struct Trie {
    replaced: u64,
    subtree: u64,
    children: HashMap<String, Trie>,
}

impl Trie {
    fn touch(&mut self, path: &[String], revision: u64) {
        self.subtree = revision;
        match path.split_first() {
            None => self.replaced = revision,
            Some((token, rest)) => self
                .children
                .entry(token.clone())
                .or_default()
                .touch(rest, revision),
        }
    }

    fn revision_at(&self, path: &[String]) -> u64 {
        let mut node = self;
        let mut best = self.replaced;
        for token in path {
            match node.children.get(token) {
                Some(child) => {
                    node = child;
                    best = best.max(child.replaced);
                }
                None => return best,
            }
        }
        best.max(node.subtree)
    }
}

struct Subscription {
    id: u64,
    paths: Vec<Vec<String>>,
    include_descendants: bool,
    listener: Arc<dyn Listener>,
    is_cancelled: Arc<AtomicBool>,
}

struct Waker {
    id: u64,
    wake: Arc<dyn Fn() + Send + Sync>,
    is_cancelled: Arc<AtomicBool>,
}

struct Inner {
    root: Node,
    revision: u64,
    trie: Trie,
    subscriptions: Vec<Subscription>,
    queue: VecDeque<(Arc<dyn Listener>, Arc<AtomicBool>, Arc<Change>)>,
    next_id: u64,
}

/// A handle that stops a subscription or waker.
pub struct SubscriptionHandle {
    store: Weak<Store>,
    id: u64,
    is_cancelled: Arc<AtomicBool>,
}

impl SubscriptionHandle {
    pub fn is_cancelled(&self) -> bool {
        self.is_cancelled.load(Ordering::SeqCst)
    }

    pub fn cancel(&self) {
        self.is_cancelled.store(true, Ordering::SeqCst);
        if let Some(store) = self.store.upgrade() {
            lock(&store.inner)
                .subscriptions
                .retain(|entry| entry.id != self.id);
            lock(&store.wakers).retain(|entry| entry.id != self.id);
        }
    }
}

/// What a caller saw and may change, for conflict-checked edits by decision systems.
#[derive(Debug, Clone)]
pub struct Observation {
    store_id: u64,
    pub revision: u64,
    pub selection: Selection,
    pub read: Vec<Vec<String>>,
    pub write: Vec<Vec<String>>,
    pub schemas: Vec<(String, Value)>,
    dependencies: Vec<(Vec<String>, u64)>,
}

/// The owner of one state tree.
pub struct Store {
    id: u64,
    schema: Schema,
    inner: Mutex<Inner>,
    wakers: Mutex<Vec<Waker>>,
    is_draining: AtomicBool,
}

impl std::fmt::Debug for Store {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(
            formatter,
            "Store(id={}, revision={})",
            self.id,
            self.revision()
        )
    }
}

fn covers(grants: &[Vec<String>], path: &[String]) -> bool {
    grants.iter().any(|grant| path.starts_with(grant))
}

fn describe(path: &[String]) -> String {
    let pointer = to_pointer(path);
    if pointer.is_empty() {
        "the root".to_owned()
    } else {
        pointer
    }
}

impl Store {
    /// Create a store holding `value`, which must satisfy `schema`.
    pub fn new(value: Node, schema: Schema) -> Result<Arc<Self>, Error> {
        schema.validate(&value)?;
        Ok(Arc::new(Self {
            id: NEXT_STORE_ID.fetch_add(1, Ordering::SeqCst),
            schema,
            inner: Mutex::new(Inner {
                root: value,
                revision: 0,
                trie: Trie::default(),
                subscriptions: Vec::new(),
                queue: VecDeque::new(),
                next_id: 1,
            }),
            wakers: Mutex::new(Vec::new()),
            is_draining: AtomicBool::new(false),
        }))
    }

    pub fn id(&self) -> u64 {
        self.id
    }

    pub fn schema(&self) -> &Schema {
        &self.schema
    }

    pub fn revision(&self) -> u64 {
        lock(&self.inner).revision
    }

    /// The most recent revision that changed `path`, an ancestor or a descendant.
    pub fn revision_at(&self, path: &[String]) -> u64 {
        lock(&self.inner).trie.revision_at(path)
    }

    /// An immutable view of the branch at `path`.
    pub fn snapshot(&self, path: &[String]) -> Result<Snapshot, Error> {
        let (root, revision) = {
            let inner = lock(&self.inner);
            (inner.root.clone(), inner.revision)
        };
        Snapshot {
            revision,
            node: root,
            schema: self.schema.clone(),
        }
        .at(path)
    }

    /// Replace the branch at `path`, publishing one commit.
    pub fn set(
        self: &Arc<Self>,
        path: &[String],
        value: Node,
        expected_revision: Option<u64>,
    ) -> Result<Option<Arc<Change>>, Error> {
        self.commit(expected_revision, |root| {
            root.with_value(path, value.clone())
        })
    }

    /// Apply a patch atomically.
    pub fn apply(
        self: &Arc<Self>,
        patch: &Patch,
        expected_revision: Option<u64>,
    ) -> Result<Option<Arc<Change>>, Error> {
        self.commit(expected_revision, |root| patch.apply(root))
    }

    fn commit(
        self: &Arc<Self>,
        expected_revision: Option<u64>,
        edit: impl FnOnce(&Node) -> Result<Node, Error>,
    ) -> Result<Option<Arc<Change>>, Error> {
        let change = {
            let mut inner = lock(&self.inner);
            if let Some(expected) = expected_revision
                && expected != inner.revision
            {
                return Err(Error::Conflict {
                    expected,
                    actual: inner.revision,
                });
            }
            let updated = edit(&inner.root)?;
            self.publish(&mut inner, updated)?
        };
        if change.is_some() {
            self.wake();
        }
        Ok(change)
    }

    fn publish(&self, inner: &mut Inner, updated: Node) -> Result<Option<Arc<Change>>, Error> {
        self.schema.validate(&updated)?;
        let changes = inner.root.diff(&updated);
        if changes.is_empty() {
            return Ok(None);
        }
        let before_revision = inner.revision;
        let revision = before_revision + 1;
        let patch = Patch::from_changes(&inner.root, &updated, &changes);
        let change = Arc::new(Change {
            before_revision,
            revision,
            paths: changes.clone(),
            patch,
            before: Snapshot {
                revision: before_revision,
                node: inner.root.clone(),
                schema: self.schema.clone(),
            },
            after: Snapshot {
                revision,
                node: updated.clone(),
                schema: self.schema.clone(),
            },
        });
        for segments in &changes {
            let tokens: Vec<String> = segments.iter().map(Segment::token).collect();
            inner.trie.touch(&tokens, revision);
        }
        inner.root = updated;
        inner.revision = revision;
        let changed: Vec<Vec<String>> = changes
            .iter()
            .map(|segments| segments.iter().map(Segment::token).collect())
            .collect();
        let mut queued = Vec::new();
        for subscription in &inner.subscriptions {
            if subscription.is_cancelled.load(Ordering::SeqCst) {
                continue;
            }
            let is_affected = subscription.paths.iter().any(|watched| {
                changed.iter().any(|path| {
                    if path.starts_with(watched) {
                        subscription.include_descendants || path.len() == watched.len()
                    } else {
                        watched.starts_with(path)
                    }
                })
            });
            if is_affected {
                queued.push((
                    Arc::clone(&subscription.listener),
                    Arc::clone(&subscription.is_cancelled),
                    Arc::clone(&change),
                ));
            }
        }
        inner.queue.extend(queued);
        Ok(Some(change))
    }

    fn wake(&self) {
        let wakers: Vec<_> = lock(&self.wakers)
            .iter()
            .filter(|waker| !waker.is_cancelled.load(Ordering::SeqCst))
            .map(|waker| Arc::clone(&waker.wake))
            .collect();
        for wake in wakers {
            wake();
        }
    }

    /// Start an isolated set of staged edits.
    pub fn transaction(self: &Arc<Self>, expected_revision: Option<u64>) -> Transaction {
        let (root, revision) = {
            let inner = lock(&self.inner);
            (inner.root.clone(), inner.revision)
        };
        Transaction {
            store: Arc::clone(self),
            base_revision: revision,
            expected_revision,
            working: root,
            operations: Vec::new(),
            is_finished: false,
        }
    }

    /// Be told about changes to `paths` when the queue is drained.
    pub fn subscribe(
        self: &Arc<Self>,
        paths: Vec<Vec<String>>,
        include_descendants: bool,
        listener: Arc<dyn Listener>,
    ) -> SubscriptionHandle {
        let mut inner = lock(&self.inner);
        let id = inner.next_id;
        inner.next_id += 1;
        let is_cancelled = Arc::new(AtomicBool::new(false));
        inner.subscriptions.push(Subscription {
            id,
            paths,
            include_descendants,
            listener,
            is_cancelled: Arc::clone(&is_cancelled),
        });
        SubscriptionHandle {
            store: Arc::downgrade(self),
            id,
            is_cancelled,
        }
    }

    /// Call `wake` after every commit, from the committing thread and outside any lock.
    pub fn attach_waker(self: &Arc<Self>, wake: Arc<dyn Fn() + Send + Sync>) -> SubscriptionHandle {
        let id = {
            let mut inner = lock(&self.inner);
            let id = inner.next_id;
            inner.next_id += 1;
            id
        };
        let is_cancelled = Arc::new(AtomicBool::new(false));
        lock(&self.wakers).push(Waker {
            id,
            wake,
            is_cancelled: Arc::clone(&is_cancelled),
        });
        SubscriptionHandle {
            store: Arc::downgrade(self),
            id,
            is_cancelled,
        }
    }

    /// Deliver up to `maximum` queued notifications on the calling thread.
    ///
    /// Listeners may commit changes; those are queued for a later call, never delivered
    /// recursively.
    pub fn drain(&self, maximum: usize) -> Result<usize, ListenerFailure> {
        struct Reset<'a>(&'a AtomicBool);
        impl Drop for Reset<'_> {
            fn drop(&mut self) {
                self.0.store(false, Ordering::SeqCst);
            }
        }
        if self.is_draining.swap(true, Ordering::SeqCst) {
            return Ok(0);
        }
        let _reset = Reset(&self.is_draining);
        let mut delivered = 0;
        while delivered < maximum {
            let Some((listener, is_cancelled, change)) = lock(&self.inner).queue.pop_front() else {
                break;
            };
            if is_cancelled.load(Ordering::SeqCst) {
                continue;
            }
            listener.notify(&change)?;
            delivered += 1;
        }
        Ok(delivered)
    }

    /// Whether notifications are waiting to be drained.
    pub fn has_pending_notifications(&self) -> bool {
        !lock(&self.inner).queue.is_empty()
    }

    /// Observe `read` branches and declare which `write` branches may change.
    pub fn observe(
        &self,
        read: Vec<Vec<String>>,
        write: Vec<Vec<String>>,
    ) -> Result<Observation, Error> {
        let inner = lock(&self.inner);
        let snapshot = Snapshot {
            revision: inner.revision,
            node: inner.root.clone(),
            schema: self.schema.clone(),
        };
        let mut schemas = Vec::new();
        let mut dependencies = Vec::new();
        for path in read.iter().chain(&write) {
            let schema = self.schema.at(path)?;
            let pointer = to_pointer(path);
            if !schemas.iter().any(|(existing, _)| existing == &pointer) {
                schemas.push((pointer, schema.to_json()));
            }
            dependencies.push((path.clone(), inner.trie.revision_at(path)));
        }
        Ok(Observation {
            store_id: self.id,
            revision: inner.revision,
            selection: snapshot.select(&read),
            read,
            write,
            schemas,
            dependencies,
        })
    }

    fn check_observation(
        &self,
        inner: &Inner,
        patch: &Patch,
        observation: &Observation,
    ) -> Result<(), Error> {
        if observation.store_id != self.id {
            return Err(Error::Access(
                "this observation came from a different state store; observe this store again \
                 before proposing a change"
                    .to_owned(),
            ));
        }
        let readable =
            |path: &[String]| covers(&observation.read, path) || covers(&observation.write, path);
        for operation in &patch.operations {
            let denied = |path: &[String], needs: &str| {
                Error::Access(format!(
                    "the patch needs {needs} access to {} but the observation does not grant it; \
                     observe that branch with {needs}=[...] before changing it",
                    describe(path)
                ))
            };
            match operation {
                PatchOperation::Add { path, .. }
                | PatchOperation::Remove { path }
                | PatchOperation::Replace { path, .. } => {
                    if !covers(&observation.write, path) {
                        return Err(denied(path, "write"));
                    }
                }
                PatchOperation::Test { path, .. } => {
                    if !readable(path) {
                        return Err(denied(path, "read"));
                    }
                }
                PatchOperation::Copy { from, path } => {
                    if !readable(from) {
                        return Err(denied(from, "read"));
                    }
                    if !covers(&observation.write, path) {
                        return Err(denied(path, "write"));
                    }
                }
                PatchOperation::Move { from, path } => {
                    if !covers(&observation.write, from) {
                        return Err(denied(from, "write"));
                    }
                    if !covers(&observation.write, path) {
                        return Err(denied(path, "write"));
                    }
                }
            }
        }
        for (path, revision) in &observation.dependencies {
            let actual = inner.trie.revision_at(path);
            if actual != *revision {
                return Err(Error::Conflict {
                    expected: *revision,
                    actual,
                });
            }
        }
        Ok(())
    }

    /// Check a patch against an observation without publishing it.
    pub fn validate_observed(&self, patch: &Patch, observation: &Observation) -> Result<(), Error> {
        let inner = lock(&self.inner);
        self.check_observation(&inner, patch, observation)?;
        let updated = patch.apply(&inner.root)?;
        self.schema.validate(&updated)
    }

    /// Apply a patch if it stays inside the observation's grants and nothing it depends
    /// on changed.
    pub fn apply_observed(
        self: &Arc<Self>,
        patch: &Patch,
        observation: &Observation,
    ) -> Result<Option<Arc<Change>>, Error> {
        let change = {
            let mut inner = lock(&self.inner);
            self.check_observation(&inner, patch, observation)?;
            let updated = patch.apply(&inner.root)?;
            self.publish(&mut inner, updated)?
        };
        if change.is_some() {
            self.wake();
        }
        Ok(change)
    }
}

enum Staged {
    Set(Vec<String>, Node),
    Remove(Vec<String>),
    Patch(Patch),
}

/// Staged edits that publish together at commit, or not at all.
pub struct Transaction {
    store: Arc<Store>,
    pub base_revision: u64,
    expected_revision: Option<u64>,
    working: Node,
    operations: Vec<Staged>,
    is_finished: bool,
}

impl Transaction {
    fn check_open(&self) -> Result<(), Error> {
        if self.is_finished {
            return Err(Error::validation(
                &[],
                "transaction",
                "the transaction is already finished; start a new transaction to make more changes",
            ));
        }
        Ok(())
    }

    /// The staged tree, as a snapshot at the base revision.
    pub fn snapshot(&self) -> Snapshot {
        Snapshot {
            revision: self.base_revision,
            node: self.working.clone(),
            schema: self.store.schema.clone(),
        }
    }

    pub fn set(&mut self, path: &[String], value: Node) -> Result<(), Error> {
        self.check_open()?;
        self.working = self.working.with_value(path, value.clone())?;
        self.operations.push(Staged::Set(path.to_vec(), value));
        Ok(())
    }

    pub fn remove(&mut self, path: &[String]) -> Result<(), Error> {
        self.check_open()?;
        self.working = self.working.without(path)?;
        self.operations.push(Staged::Remove(path.to_vec()));
        Ok(())
    }

    pub fn apply(&mut self, patch: &Patch) -> Result<(), Error> {
        self.check_open()?;
        self.working = patch.apply(&self.working)?;
        self.operations.push(Staged::Patch(patch.clone()));
        Ok(())
    }

    /// Publish every staged edit as one commit.
    ///
    /// The edits are replayed on the latest tree, so unrelated changes made since the
    /// transaction began are kept. When the transaction was started with an expected
    /// revision, any change since then is a conflict instead.
    pub fn commit(&mut self) -> Result<Option<Arc<Change>>, Error> {
        self.check_open()?;
        self.is_finished = true;
        let operations = std::mem::take(&mut self.operations);
        self.store.commit(self.expected_revision, |root| {
            let mut current = root.clone();
            for staged in &operations {
                current = match staged {
                    Staged::Set(path, value) => current.with_value(path, value.clone())?,
                    Staged::Remove(path) => current.without(path)?,
                    Staged::Patch(patch) => patch.apply(&current)?,
                };
            }
            Ok(current)
        })
    }

    /// Discard every staged edit.
    pub fn rollback(&mut self) {
        self.is_finished = true;
        self.operations.clear();
    }

    pub fn is_finished(&self) -> bool {
        self.is_finished
    }
}
