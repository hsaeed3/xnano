//! Buffers: canonical content, geometry and a tree of retained layers.
//!
//! A [`BufferCore`] owns one [`Grid`] of cells and any number of attached children. All
//! positions are relative to the parent. Every change bumps a revision and records the
//! damaged area, which is how a runtime knows when a frame is needed.

use std::fmt;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex, MutexGuard, Weak};

use ratatui_core::buffer::Cell;

use crate::geometry::{MAXIMUM_DIMENSION, Rectangle, Size};
use crate::grid::{Bounds, Grid, MAXIMUM_CELLS, PasteMode};
use crate::layout::{LayoutSpec, solve};

static NEXT_ID: AtomicU64 = AtomicU64::new(1);
static MODIFICATION_STAMP: AtomicU64 = AtomicU64::new(1);
/// How many buffers take the size of their children, so the fitting pass is skipped while
/// there are none.
static FITTED_BUFFERS: AtomicUsize = AtomicUsize::new(0);

/// Whether any buffer fits its content, so that what decides a size has to be followed.
pub fn is_fitting_anywhere() -> bool {
    FITTED_BUFFERS.load(Ordering::Relaxed) > 0
}

/// A buffer that takes the size of the children it holds.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Fit {
    /// Whether the width follows the children: as wide as the farthest right edge.
    pub width: bool,
    /// Whether the height follows the children: as tall as the lowest bottom edge.
    pub height: bool,
    /// Columns after the farthest right edge, for a border or padding on that side.
    pub trailing_columns: u16,
    /// Rows below the lowest bottom edge, for a border or padding on that side.
    pub trailing_rows: u16,
}

/// The parts of a child's place that its parent's size decides: a percentage, a word such as
/// `center` or a formula of the parent's size. A parent that fits its children places such
/// a child within the size the others give it instead of growing to it.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct ParentMeasured {
    pub x: bool,
    pub y: bool,
    pub width: bool,
    pub height: bool,
}

/// Called after any buffer changes, from the thread that changed it.
pub type ChangeListener = Arc<dyn Fn() + Send + Sync>;

static CHANGE_LISTENERS: Mutex<Vec<(u64, ChangeListener)>> = Mutex::new(Vec::new());
/// How many listeners are registered, so a change with none to tell costs one atomic read.
static CHANGE_LISTENER_COUNT: AtomicUsize = AtomicUsize::new(0);
static NEXT_CHANGE_LISTENER: AtomicU64 = AtomicU64::new(1);

fn change_listeners() -> MutexGuard<'static, Vec<(u64, ChangeListener)>> {
    CHANGE_LISTENERS
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
}

/// Keeps a change listener registered until it is dropped.
#[must_use = "the listener is removed as soon as the registration is dropped"]
pub struct ChangeListenerRegistration {
    id: u64,
}

impl Drop for ChangeListenerRegistration {
    fn drop(&mut self) {
        let mut listeners = change_listeners();
        if let Some(index) = listeners.iter().position(|(id, _)| *id == self.id) {
            listeners.swap_remove(index);
            CHANGE_LISTENER_COUNT.fetch_sub(1, Ordering::SeqCst);
        }
    }
}

/// Call `listener` after every buffer change until the registration is dropped.
///
/// A runtime that is waiting for work listens while it waits, so a change made from
/// another thread is drawn at once instead of when the wait would have ended.
pub fn listen_for_changes(listener: ChangeListener) -> ChangeListenerRegistration {
    let id = NEXT_CHANGE_LISTENER.fetch_add(1, Ordering::SeqCst);
    change_listeners().push((id, listener));
    CHANGE_LISTENER_COUNT.fetch_add(1, Ordering::SeqCst);
    ChangeListenerRegistration { id }
}

fn announce_change() {
    if CHANGE_LISTENER_COUNT.load(Ordering::SeqCst) == 0 {
        return;
    }
    let listeners: Vec<ChangeListener> = change_listeners()
        .iter()
        .map(|(_, listener)| Arc::clone(listener))
        .collect();
    for listener in listeners {
        listener();
    }
}

/// Who decides a child's position and size.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Geometry {
    /// The parent's layout does.
    Inherit,
    /// The child keeps the position and size it was given.
    Explicit,
}

impl Geometry {
    pub fn from_name(name: &str) -> Option<Self> {
        Some(match name {
            "inherit" => Self::Inherit,
            "explicit" => Self::Explicit,
            _ => return None,
        })
    }

    pub fn name(self) -> &'static str {
        match self {
            Self::Inherit => "inherit",
            Self::Explicit => "explicit",
        }
    }
}

/// An attached child and how it joins its parent.
#[derive(Clone)]
pub struct Child {
    pub core: Arc<BufferCore>,
    pub geometry: Geometry,
    pub mode: PasteMode,
}

/// Why a tree change was refused.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum TreeError {
    AttachToSelf,
    AlreadyAttached,
    WouldCycle,
    NotAChild,
    ChildMounted,
}

impl fmt::Display for TreeError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::AttachToSelf => "a buffer cannot be attached to itself",
            Self::AlreadyAttached => {
                "the buffer is already attached to a parent; detach it from that parent first"
            }
            Self::WouldCycle => {
                "the buffer is an ancestor of the one it would be attached to, which would make a loop"
            }
            Self::NotAChild => "the buffer is not attached to this parent",
            Self::ChildMounted => {
                "the buffer is mounted on a runtime; unmount it before attaching it to a parent"
            }
        })
    }
}

impl std::error::Error for TreeError {}

pub struct BufferState {
    pub x: i32,
    pub y: i32,
    pub grid: Grid,
    pub layer: i32,
    pub is_visible: bool,
    pub is_focusable: bool,
    /// Counts this buffer's own changes.
    pub revision: u64,
    /// A process-wide stamp of the latest change, comparable across buffers.
    pub modified: u64,
    /// The cell used for new area and for clearing.
    pub fill: Cell,
    pub children: Vec<Child>,
    pub parent: Weak<BufferCore>,
    pub layout: Option<LayoutSpec>,
    /// The size the buffer was given directly, which `fit` layouts use.
    pub intrinsic: Size,
    pub is_mounted: bool,
    pub damage: Vec<Rectangle>,
    /// Data an embedding layer (such as the Python bindings) keeps with the buffer.
    pub extension: Option<Arc<dyn std::any::Any + Send + Sync>>,
    /// Produces the cells of a retained widget; `None` for plain buffers.
    pub painter: Option<Arc<dyn crate::painter::Painter>>,
    /// The fingerprint of the inputs the cells were last painted from.
    pub painted: Option<u64>,
    /// How the size follows the children; `None` keeps the size the buffer is given.
    pub fit: Option<Fit>,
    /// The parts of the buffer's place that its parent's size decides.
    pub parent_measured: ParentMeasured,
}

impl BufferState {
    /// Record a change to `area` (local coordinates), or to everything when `None`.
    pub fn touch(&mut self, area: Option<Rectangle>) {
        self.revision += 1;
        self.modified = MODIFICATION_STAMP.fetch_add(1, Ordering::SeqCst);
        announce_change();
        let area = area.unwrap_or_else(|| {
            Rectangle::new(
                0,
                0,
                i32::from(self.grid.width()),
                i32::from(self.grid.height()),
            )
        });
        if self.damage.len() >= 16 {
            let merged = self.damage.drain(..).fold(area, Rectangle::union);
            self.damage.push(merged);
        } else {
            self.damage.push(area);
        }
    }

    pub fn width(&self) -> i32 {
        i32::from(self.grid.width())
    }

    pub fn height(&self) -> i32 {
        i32::from(self.grid.height())
    }

    pub fn bounds(&self) -> Rectangle {
        Rectangle::new(self.x, self.y, self.width(), self.height())
    }

    pub fn full_bounds(&self) -> Bounds {
        self.grid.bounds()
    }
}

/// One buffer and its place in the tree.
pub struct BufferCore {
    pub id: u64,
    state: Mutex<BufferState>,
}

impl Drop for BufferCore {
    fn drop(&mut self) {
        let state = self
            .state
            .get_mut()
            .unwrap_or_else(std::sync::PoisonError::into_inner);
        if state.fit.is_some() {
            FITTED_BUFFERS.fetch_sub(1, Ordering::SeqCst);
        }
    }
}

impl fmt::Debug for BufferCore {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "BufferCore({})", self.id)
    }
}

/// Check a requested size against what a terminal and memory can hold.
pub fn check_size(width: i32, height: i32) -> Result<(u16, u16), String> {
    if width < 0 || height < 0 {
        return Err(format!(
            "a buffer cannot be {width} x {height}: the width and height must be zero or more"
        ));
    }
    if width > MAXIMUM_DIMENSION || height > MAXIMUM_DIMENSION {
        return Err(format!(
            "a buffer cannot be {width} x {height}: the width and height are limited to \
             {MAXIMUM_DIMENSION} cells each"
        ));
    }
    if (width as usize) * (height as usize) > MAXIMUM_CELLS {
        return Err(format!(
            "a buffer of {width} x {height} has {} cells; the limit is {MAXIMUM_CELLS} cells, \
             so use a smaller width or height",
            (width as usize) * (height as usize)
        ));
    }
    Ok((width as u16, height as u16))
}

impl BufferCore {
    pub fn new(grid: Grid, x: i32, y: i32, fill: Cell) -> Arc<Self> {
        let intrinsic = Size::new(i32::from(grid.width()), i32::from(grid.height()));
        Arc::new(Self {
            id: NEXT_ID.fetch_add(1, Ordering::SeqCst),
            state: Mutex::new(BufferState {
                x,
                y,
                grid,
                layer: 0,
                is_visible: true,
                is_focusable: false,
                revision: 0,
                modified: MODIFICATION_STAMP.fetch_add(1, Ordering::SeqCst),
                fill,
                children: Vec::new(),
                parent: Weak::new(),
                layout: None,
                intrinsic,
                is_mounted: false,
                damage: Vec::new(),
                extension: None,
                painter: None,
                painted: None,
                fit: None,
                parent_measured: ParentMeasured::default(),
            }),
        })
    }

    /// Make the buffer take the size of its children, or keep the size it is given (`None`).
    pub fn set_fit(&self, fit: Option<Fit>) {
        let mut state = self.lock();
        match (state.fit.is_some(), fit.is_some()) {
            (false, true) => {
                FITTED_BUFFERS.fetch_add(1, Ordering::SeqCst);
            }
            (true, false) => {
                FITTED_BUFFERS.fetch_sub(1, Ordering::SeqCst);
            }
            _ => {}
        }
        state.fit = fit;
        state.touch(None);
    }

    pub fn lock(&self) -> MutexGuard<'_, BufferState> {
        self.state
            .lock()
            .unwrap_or_else(std::sync::PoisonError::into_inner)
    }

    pub fn parent(&self) -> Option<Arc<BufferCore>> {
        self.lock().parent.upgrade()
    }

    /// Set the size the buffer was given directly, then rearrange the parent if needed.
    pub fn resize(self: &Arc<Self>, width: i32, height: i32) -> Result<(), String> {
        let (columns, rows) = check_size(width, height)?;
        {
            let mut state = self.lock();
            state.intrinsic = Size::new(width, height);
            let fill = state.fill.clone();
            state.grid.resize(columns, rows, &fill);
            state.touch(None);
        }
        relayout(self);
        if let Some(parent) = self.parent() {
            relayout(&parent);
        }
        Ok(())
    }

    /// Set the size from a layout; unlike [`BufferCore::resize`] the intrinsic size stays.
    fn assign_geometry(&self, rectangle: Rectangle) -> bool {
        let (columns, rows) =
            check_size(rectangle.width.max(0), rectangle.height.max(0)).unwrap_or((0, 0));
        let mut state = self.lock();
        let changed_size = state.grid.width() != columns || state.grid.height() != rows;
        let changed = changed_size || state.x != rectangle.x || state.y != rectangle.y;
        if changed {
            state.x = rectangle.x;
            state.y = rectangle.y;
            let fill = state.fill.clone();
            state.grid.resize(columns, rows, &fill);
            state.touch(None);
        }
        changed_size
    }

    pub fn move_to(&self, x: i32, y: i32) {
        let mut state = self.lock();
        if state.x != x || state.y != y {
            // Both the old and new coverage need repainting.
            state.touch(None);
            state.x = x;
            state.y = y;
            state.touch(None);
        }
    }
}

/// Arrange the inherited children of `core` according to its layout, recursively.
pub fn relayout(core: &Arc<BufferCore>) {
    let plan = {
        let state = core.lock();
        let inherited: Vec<&Child> = state
            .children
            .iter()
            .filter(|child| child.geometry == Geometry::Inherit)
            .collect();
        if inherited.is_empty() {
            return;
        }
        let spec = state.layout.clone().unwrap_or(LayoutSpec {
            arrangement: crate::layout::Arrangement::Overlay,
            ..LayoutSpec::default()
        });
        let intrinsic: Vec<Size> = inherited
            .iter()
            .map(|child| child.core.lock().intrinsic)
            .collect();
        let area = Rectangle::new(0, 0, state.width(), state.height());
        let rectangles = solve(&spec, area, &intrinsic);
        inherited
            .iter()
            .map(|child| Arc::clone(&child.core))
            .zip(rectangles)
            .collect::<Vec<_>>()
    };
    for (child, rectangle) in plan {
        if child.assign_geometry(rectangle) {
            relayout(&child);
        }
    }
}

/// The cells a buffer's children cover from its top-left corner: the farthest right edge and
/// the lowest bottom edge among its visible children with explicit geometry.
///
/// A child the parent's size places or sizes (see [`ParentMeasured`]) is placed within the
/// size the other children give: one placed by its parent's size counts with its own size,
/// and one sized by it does not count along that axis.
pub fn content_extent(core: &Arc<BufferCore>) -> Size {
    let state = core.lock();
    let mut right = 0;
    let mut bottom = 0;
    for child in &state.children {
        if child.geometry != Geometry::Explicit {
            continue;
        }
        let child_state = child.core.lock();
        if !child_state.is_visible {
            continue;
        }
        let measured = child_state.parent_measured;
        let (width, height) = (child_state.width(), child_state.height());
        let child_right = if measured.width {
            0
        } else if measured.x {
            width
        } else {
            child_state.x + width
        };
        let child_bottom = if measured.height {
            0
        } else if measured.y {
            height
        } else {
            child_state.y + height
        };
        right = right.max(child_right);
        bottom = bottom.max(child_bottom);
    }
    Size::new(right.max(0), bottom.max(0))
}

/// Give every buffer under `core` (and `core` itself) that fits its children the size they
/// cover, deepest first, so a fitted buffer inside another is sized before its parent.
/// Returns whether a size changed. Does nothing while no buffer fits its children.
pub fn fit_tree(core: &Arc<BufferCore>) -> bool {
    if FITTED_BUFFERS.load(Ordering::SeqCst) == 0 {
        return false;
    }
    fit_subtree(core)
}

fn fit_subtree(core: &Arc<BufferCore>) -> bool {
    let children: Vec<Arc<BufferCore>> = core
        .lock()
        .children
        .iter()
        .map(|child| Arc::clone(&child.core))
        .collect();
    let mut is_changed = false;
    for child in &children {
        is_changed |= fit_subtree(child);
    }
    let (fit, width, height) = {
        let state = core.lock();
        (state.fit, state.width(), state.height())
    };
    let Some(fit) = fit else {
        return is_changed;
    };
    let extent = content_extent(core);
    let fitted_width = if fit.width {
        (extent.width + i32::from(fit.trailing_columns)).max(1)
    } else {
        width
    };
    let fitted_height = if fit.height {
        (extent.height + i32::from(fit.trailing_rows)).max(1)
    } else {
        height
    };
    if (fitted_width, fitted_height) != (width, height)
        && core.resize(fitted_width, fitted_height).is_ok()
    {
        is_changed = true;
    }
    is_changed
}

/// Whether `ancestor` is `core` or one of its ancestors.
fn is_ancestor(ancestor: &Arc<BufferCore>, core: &Arc<BufferCore>) -> bool {
    let mut current = Some(Arc::clone(core));
    while let Some(node) = current {
        if Arc::ptr_eq(&node, ancestor) {
            return true;
        }
        current = node.parent();
    }
    false
}

/// Attach `child` to `parent`.
pub fn attach(
    parent: &Arc<BufferCore>,
    child: &Arc<BufferCore>,
    geometry: Geometry,
    mode: PasteMode,
) -> Result<(), TreeError> {
    if Arc::ptr_eq(parent, child) {
        return Err(TreeError::AttachToSelf);
    }
    if child.parent().is_some() {
        return Err(TreeError::AlreadyAttached);
    }
    if is_ancestor(child, parent) {
        return Err(TreeError::WouldCycle);
    }
    if child.lock().is_mounted {
        return Err(TreeError::ChildMounted);
    }
    {
        let is_visible = {
            let mut child_state = child.lock();
            child_state.parent = Arc::downgrade(parent);
            child_state.is_visible
        };
        let mut state = parent.lock();
        state.children.push(Child {
            core: Arc::clone(child),
            geometry,
            mode,
        });
        // A hidden child changes nothing that is drawn; it touches its parent when shown.
        if is_visible {
            state.touch(None);
        }
    }
    relayout(parent);
    Ok(())
}

/// Detach `child` from `parent`.
pub fn detach(parent: &Arc<BufferCore>, child: &Arc<BufferCore>) -> Result<(), TreeError> {
    {
        let mut state = parent.lock();
        let Some(position) = state
            .children
            .iter()
            .position(|entry| Arc::ptr_eq(&entry.core, child))
        else {
            return Err(TreeError::NotAChild);
        };
        state.children.remove(position);
        state.touch(None);
    }
    child.lock().parent = Weak::new();
    relayout(parent);
    Ok(())
}

/// Where the top-left cell of `core` is, in the coordinates of its root.
pub fn absolute_origin(core: &Arc<BufferCore>) -> (i32, i32) {
    let mut origin = (0_i32, 0_i32);
    let mut current = Some(Arc::clone(core));
    while let Some(node) = current {
        let state = node.lock();
        origin.0 = origin.0.saturating_add(state.x);
        origin.1 = origin.1.saturating_add(state.y);
        let parent = state.parent.upgrade();
        drop(state);
        current = parent;
    }
    origin
}

/// The children of `core` in paint order: lowest layer first, attachment order within a layer.
pub fn paint_order(core: &Arc<BufferCore>) -> Vec<Child> {
    let children: Vec<Child> = core.lock().children.clone();
    // Each child's layer is read once, and the stable sort keeps attachment order within a layer.
    let mut keyed: Vec<_> = children
        .into_iter()
        .map(|child| {
            let layer = child.core.lock().layer;
            (layer, child)
        })
        .collect();
    keyed.sort_by_key(|(layer, _)| *layer);
    keyed.into_iter().map(|(_, child)| child).collect()
}

fn clip_to_bounds(clip: Rectangle, grid: &Grid) -> Option<Bounds> {
    let area = clip.intersection(Rectangle::new(
        0,
        0,
        i32::from(grid.width()),
        i32::from(grid.height()),
    ));
    if area.is_empty() {
        return None;
    }
    Some(Bounds {
        left: area.x as u16,
        top: area.y as u16,
        right: area.right() as u16,
        bottom: area.bottom() as u16,
    })
}

/// Paint `core` and its visible descendants onto `output`.
///
/// `origin` is where the parent's top-left cell sits in `output`; `clip` limits painting
/// to the parent's visible area.
pub fn compose(
    core: &Arc<BufferCore>,
    output: &mut Grid,
    origin: (i32, i32),
    clip: Rectangle,
    mode: PasteMode,
) {
    let (area, visible) = {
        let state = core.lock();
        if !state.is_visible {
            return;
        }
        let area = Rectangle::new(
            origin.0.saturating_add(state.x),
            origin.1.saturating_add(state.y),
            state.width(),
            state.height(),
        );
        let visible = clip.intersection(area);
        if visible.is_empty() {
            return;
        }
        if let Some(bounds) = clip_to_bounds(visible, output) {
            output.paste(
                bounds,
                &state.grid,
                area.x - i32::from(bounds.left),
                area.y - i32::from(bounds.top),
                mode,
            );
        }
        (area, visible)
    };
    for child in paint_order(core) {
        compose(&child.core, output, (area.x, area.y), visible, child.mode);
    }
}

/// The newest modification stamp handed out to any buffer. A tree whose stamps are all at or
/// below a value read earlier from this has not changed since.
pub fn latest_modification_stamp() -> u64 {
    MODIFICATION_STAMP.load(Ordering::SeqCst)
}

/// The largest modification stamp in the tree below and including `core`.
///
/// Hidden children and everything below them are left out: nothing they hold is drawn, so
/// changing them needs no frame. Showing or hiding a child touches it and its parent, so
/// that change itself is seen.
pub fn tree_modified(core: &Arc<BufferCore>) -> u64 {
    let (own, children): (u64, Vec<Arc<BufferCore>>) = {
        let state = core.lock();
        (
            state.modified,
            state
                .children
                .iter()
                .map(|child| Arc::clone(&child.core))
                .collect(),
        )
    };
    children
        .iter()
        .filter(|child| child.lock().is_visible)
        .map(tree_modified)
        .fold(own, u64::max)
}

/// Visit `core` and every descendant, parents before children.
pub fn walk(core: &Arc<BufferCore>, visit: &mut impl FnMut(&Arc<BufferCore>)) {
    visit(core);
    let children: Vec<Arc<BufferCore>> = core
        .lock()
        .children
        .iter()
        .map(|child| Arc::clone(&child.core))
        .collect();
    for child in &children {
        walk(child, visit);
    }
}

/// Buffers under the point (in `root` coordinates), topmost first.
pub fn buffers_at(root: &Arc<BufferCore>, column: i32, row: i32) -> Vec<Arc<BufferCore>> {
    fn collect(
        core: &Arc<BufferCore>,
        origin: (i32, i32),
        clip: Rectangle,
        order: &mut Vec<(Arc<BufferCore>, Rectangle)>,
    ) {
        let area = {
            let state = core.lock();
            if !state.is_visible {
                return;
            }
            Rectangle::new(
                origin.0.saturating_add(state.x),
                origin.1.saturating_add(state.y),
                state.width(),
                state.height(),
            )
        };
        let visible = clip.intersection(area);
        order.push((Arc::clone(core), visible));
        for child in paint_order(core) {
            collect(&child.core, (area.x, area.y), visible, order);
        }
    }
    let mut order = Vec::new();
    collect(
        root,
        (0, 0),
        Rectangle::new(i32::MIN / 2, i32::MIN / 2, i32::MAX, i32::MAX),
        &mut order,
    );
    order
        .into_iter()
        .rev()
        .filter(|(_, visible)| visible.contains(crate::geometry::Point::new(column, row)))
        .map(|(core, _)| core)
        .collect()
}
