use std::collections::HashMap;

use pyo3::prelude::*;
use ratatui::buffer::Buffer;
use ratatui::layout::{Position, Rect};
use ratatui::layout::Layout;
use ratatui::Frame;

use super::content_bridge::{render_content, PyRenderContent};
use super::super::layout::{PyConstraint, PyDirection, PyMargin};

#[pyclass(name = "CoreRenderNode", module = "xnano_core.rust.engine", unsendable, from_py_object)]
#[derive(Clone)]
pub struct PyRenderNode {
    pub(crate) x: Option<u16>,
    pub(crate) y: Option<u16>,
    pub(crate) width: Option<u16>,
    pub(crate) height: Option<u16>,
    pub(crate) direction: Option<PyDirection>,
    pub(crate) gap: u16,
    pub(crate) constraints: Vec<PyConstraint>,
    pub(crate) margin: Option<PyMargin>,
    pub(crate) content: PyRenderContent,
    pub(crate) cursor_hint: Option<(u16, u16)>,
    pub(crate) effect_key: Option<String>,
    pub(crate) z: i32,
    pub(crate) visible: bool,
    pub(crate) children: Vec<PyRenderNode>,
}

impl PyRenderNode {
    fn make(
        x: Option<u16>,
        y: Option<u16>,
        width: Option<u16>,
        height: Option<u16>,
        direction: Option<PyDirection>,
        gap: u16,
        constraints: Option<Vec<PyConstraint>>,
        margin: Option<PyMargin>,
        content: Option<PyRenderContent>,
        cursor_hint: Option<(u16, u16)>,
        effect_key: Option<String>,
        z: i32,
        visible: bool,
        children: Option<Vec<PyRenderNode>>,
    ) -> Self {
        Self {
            x,
            y,
            width,
            height,
            direction,
            gap,
            constraints: constraints.unwrap_or_default(),
            margin,
            content: content.unwrap_or_else(PyRenderContent::empty),
            cursor_hint,
            effect_key,
            z,
            visible,
            children: children.unwrap_or_default(),
        }
    }
}

#[pymethods]
impl PyRenderNode {
    #[new]
    #[pyo3(signature = (
        *,
        x = None, y = None, width = None, height = None,
        direction = None, gap = 0, constraints = None, margin = None,
        content = None, cursor_hint = None, effect_key = None,
        z = 0, visible = true,
        children = None,
    ))]
    fn new(
        x: Option<u16>,
        y: Option<u16>,
        width: Option<u16>,
        height: Option<u16>,
        direction: Option<PyDirection>,
        gap: u16,
        constraints: Option<Vec<PyConstraint>>,
        margin: Option<PyMargin>,
        content: Option<PyRenderContent>,
        cursor_hint: Option<(u16, u16)>,
        effect_key: Option<String>,
        z: i32,
        visible: bool,
        children: Option<Vec<PyRenderNode>>,
    ) -> Self {
        Self::make(
            x, y, width, height, direction, gap, constraints, margin, content, cursor_hint,
            effect_key, z, visible, children,
        )
    }

    #[staticmethod]
    fn leaf(content: PyRenderContent) -> Self {
        Self::make(
            None, None, None, None, None, 0, None, None, Some(content), None, None, 0, true,
            None,
        )
    }

    #[staticmethod]
    #[pyo3(signature = (children, *, constraints = None, gap = 0, margin = None))]
    fn row(
        children: Vec<PyRenderNode>,
        constraints: Option<Vec<PyConstraint>>,
        gap: u16,
        margin: Option<PyMargin>,
    ) -> Self {
        Self::make(
            None,
            None,
            None,
            None,
            Some(PyDirection::Horizontal),
            gap,
            constraints,
            margin,
            None,
            None,
            None,
            0,
            true,
            Some(children),
        )
    }

    #[staticmethod]
    #[pyo3(signature = (children, *, constraints = None, gap = 0, margin = None))]
    fn column(
        children: Vec<PyRenderNode>,
        constraints: Option<Vec<PyConstraint>>,
        gap: u16,
        margin: Option<PyMargin>,
    ) -> Self {
        Self::make(
            None,
            None,
            None,
            None,
            Some(PyDirection::Vertical),
            gap,
            constraints,
            margin,
            None,
            None,
            None,
            0,
            true,
            Some(children),
        )
    }

    #[staticmethod]
    fn stack(x: u16, y: u16, width: u16, height: u16, children: Vec<PyRenderNode>) -> Self {
        Self::make(
            Some(x),
            Some(y),
            Some(width),
            Some(height),
            None,
            0,
            None,
            None,
            None,
            None,
            None,
            0,
            true,
            Some(children),
        )
    }

    fn get_children(&self) -> Vec<PyRenderNode> {
        self.children.clone()
    }

    fn get_content(&self) -> PyRenderContent {
        self.content.clone()
    }

    fn get_effect_key(&self) -> Option<String> {
        self.effect_key.clone()
    }

    fn get_z(&self) -> i32 {
        self.z
    }

    fn is_visible(&self) -> bool {
        self.visible
    }

    fn has_absolute_geometry(&self) -> bool {
        self.x.is_some()
            && self.y.is_some()
            && self.width.is_some()
            && self.height.is_some()
    }
}

impl PyRenderNode {
    pub(crate) fn absolute_rect(&self) -> Rect {
        Rect::new(
            self.x.unwrap_or(0),
            self.y.unwrap_or(0),
            self.width.unwrap_or(0),
            self.height.unwrap_or(0),
        )
    }
}

#[derive(Default)]
pub(crate) struct RenderContext {
    pub effect_areas: HashMap<String, Rect>,
    pub error: Option<PyErr>,
}

impl RenderContext {
    pub fn record_effect_area(&mut self, key: String, rect: Rect) {
        self.effect_areas.insert(key, rect);
    }
}

fn apply_margin(rect: Rect, margin: &PyMargin) -> Rect {
    rect.inner(margin.inner)
}

pub(crate) fn render_node(
    frame: &mut Frame<'_>,
    area: Rect,
    node: &PyRenderNode,
    ctx: &mut RenderContext,
) -> PyResult<Option<Position>> {
    render_node_to_buffer(frame.buffer_mut(), area, node, ctx)
}

pub(crate) fn render_node_to_buffer(
    buffer: &mut Buffer,
    area: Rect,
    node: &PyRenderNode,
    ctx: &mut RenderContext,
) -> PyResult<Option<Position>> {
    if !node.visible {
        return Ok(None);
    }

    let rect = if node.has_absolute_geometry() {
        // Clamp to the buffer's current bounds so that a terminal resize
        // occurring between layout and commit never causes an out-of-bounds
        // buffer index (the ratatui panic "index outside of buffer").
        let abs = node.absolute_rect();
        abs.intersection(buffer.area)
    } else {
        area
    };

    if rect.is_empty() {
        return Ok(None);
    }

    if let Some(key) = &node.effect_key {
        ctx.record_effect_area(key.clone(), rect);
    }

    if let Err(err) = render_content(&node.content, rect, buffer) {
        ctx.error = Some(err);
        return Ok(None);
    }

    let mut cursor_target = node.cursor_hint.map(|(dx, dy)| {
        Position::new(rect.x.saturating_add(dx), rect.y.saturating_add(dy))
    });

    if !node.children.is_empty() {
        let inner_rect = match &node.margin {
            Some(m) => apply_margin(rect, m),
            None => rect,
        };

        let absolute_children = node.children.iter().all(|c| c.has_absolute_geometry());
        let child_areas = if absolute_children {
            None
        } else {
            Some(
                Layout::default()
                    .direction(
                        node.direction
                            .map(Into::into)
                            .unwrap_or(ratatui::layout::Direction::Vertical),
                    )
                    .constraints(node.constraints.iter().map(|c| c.inner))
                    .spacing(node.gap)
                    .split(inner_rect),
            )
        };

        let needs_sort = node.children.windows(2).any(|pair| pair[0].z > pair[1].z);
        if needs_sort {
            let mut order: Vec<usize> = (0..node.children.len()).collect();
            order.sort_by_key(|&i| node.children[i].z);
            for i in order {
                let child_area = match &child_areas {
                    Some(areas) => areas[i],
                    None => node.children[i].absolute_rect().intersection(buffer.area),
                };
                if let Some(pos) = render_node_to_buffer(
                    buffer,
                    child_area,
                    &node.children[i],
                    ctx,
                )? {
                    cursor_target = Some(pos);
                }
            }
        } else if let Some(areas) = child_areas {
            for (child, child_area) in node.children.iter().zip(areas.iter()) {
                if let Some(pos) = render_node_to_buffer(buffer, *child_area, child, ctx)? {
                    cursor_target = Some(pos);
                }
            }
        } else {
            for child in &node.children {
                let child_area = child.absolute_rect().intersection(buffer.area);
                if let Some(pos) = render_node_to_buffer(buffer, child_area, child, ctx)? {
                    cursor_target = Some(pos);
                }
            }
        }
    }

    Ok(cursor_target)
}

pub fn register_render_tree(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<PyRenderNode>()?;
    Ok(())
}
