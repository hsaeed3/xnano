//! Editable chart settings and retained plotting widgets.
use crate::widgets::block::block_arg;
use crate::widgets::canvas::{
    Owners, coordinates_arg, marker_arg, optional_out, pair_arg, pair_out, present, string_out,
    widget_with_core,
};
use crate::widgets::style::{style_spec_arg, style_spec_to_py};
use crate::widgets::{Frame, PyWidget, dynamic_f64, dynamic_string, repaint};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyTuple;
use std::sync::Arc;
use xnano_terminal_runtime::dynamic::Dynamic;
use xnano_terminal_runtime::painter::Spec;
use xnano_terminal_runtime::widgets::Shared;
use xnano_terminal_runtime::widgets::chart::{AxisSpec, ChartSpec, DatasetSpec};

fn alignment_arg(value: &str) -> PyResult<ratatui_core::layout::Alignment> {
    match value {
        "left" => Ok(ratatui_core::layout::Alignment::Left),
        "center" => Ok(ratatui_core::layout::Alignment::Center),
        "right" => Ok(ratatui_core::layout::Alignment::Right),
        _ => Err(PyValueError::new_err(
            "an axis alignment must be left, center or right",
        )),
    }
}
fn graph_type_arg(value: &Bound<'_, PyAny>) -> PyResult<Dynamic<String>> {
    let setting = dynamic_string(value)?;
    if let Dynamic::Fixed(name) = &setting
        && !["scatter", "line", "bar"].contains(&name.as_str())
    {
        return Err(PyValueError::new_err(
            "a graph type must be scatter, line or bar",
        ));
    }
    Ok(setting)
}

#[pyclass(name = "ChartAxis", module = "xnano_core._xnano_core")]
pub struct PyChartAxis {
    pub spec: Shared<AxisSpec>,
    owners: Owners,
}
#[pymethods]
impl PyChartAxis {
    #[new]
    #[pyo3(signature = (*, title = None, bounds = None, labels = None, style = None, labels_alignment = None))]
    fn new(
        title: Option<&Bound<'_, PyAny>>,
        bounds: Option<&Bound<'_, PyAny>>,
        labels: Option<&Bound<'_, PyAny>>,
        style: Option<&Bound<'_, PyAny>>,
        labels_alignment: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        let mut spec = AxisSpec::default();
        if let Some(value) = present(title) {
            spec.title = present(Some(value)).map(dynamic_string).transpose()?;
        }
        if let Some(value) = present(bounds) {
            spec.bounds = pair_arg(value, "bounds")?;
        }
        if let Some(value) = present(labels) {
            spec.labels = value
                .try_iter()?
                .map(|item| dynamic_string(&item?))
                .collect::<PyResult<Vec<_>>>()?;
        }
        if let Some(value) = present(style) {
            spec.style = style_spec_arg(Some(value))?;
        }
        if let Some(value) = present(labels_alignment) {
            spec.labels_alignment = alignment_arg(value.extract::<String>()?.as_str())?;
        }
        Ok(Self {
            spec: Spec::new(spec),
            owners: Owners::default(),
        })
    }
    #[getter]
    fn title<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let _ = py;
        optional_out(py, self.spec.read().title.as_ref(), string_out)
    }
    #[setter]
    fn set_title(&self, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let setting = present(value).map(dynamic_string).transpose()?;
        self.spec.edit(|spec| spec.title = setting);
        self.owners.repaint();
        Ok(())
    }
    #[getter]
    fn bounds<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyTuple>> {
        let _ = py;
        pair_out(py, &self.spec.read().bounds)
    }
    #[setter]
    fn set_bounds(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting = pair_arg(value, "bounds")?;
        self.spec.edit(|spec| spec.bounds = setting);
        self.owners.repaint();
        Ok(())
    }
    #[getter]
    fn labels(&self, py: Python<'_>) -> PyResult<Vec<Py<PyAny>>> {
        let _ = py;
        self.spec
            .read()
            .labels
            .iter()
            .map(|value| string_out(py, value).map(Bound::unbind))
            .collect()
    }
    #[setter]
    fn set_labels(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting = value
            .try_iter()?
            .map(|item| dynamic_string(&item?))
            .collect::<PyResult<Vec<_>>>()?;
        self.spec.edit(|spec| spec.labels = setting);
        self.owners.repaint();
        Ok(())
    }
    #[getter]
    fn style(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let _ = py;
        style_spec_to_py(py, &self.spec.read().style)
    }
    #[setter]
    fn set_style(&self, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let setting = style_spec_arg(value)?;
        self.spec.edit(|spec| spec.style = setting);
        self.owners.repaint();
        Ok(())
    }
    #[getter]
    fn labels_alignment(&self, py: Python<'_>) -> PyResult<String> {
        let _ = py;
        Ok(format!("{:?}", self.spec.read().labels_alignment).to_lowercase())
    }
    #[setter]
    fn set_labels_alignment(&self, value: &str) -> PyResult<()> {
        let setting = alignment_arg(value)?;
        self.spec.edit(|spec| spec.labels_alignment = setting);
        self.owners.repaint();
        Ok(())
    }
    fn __copy__(&self) -> Self {
        Self {
            spec: Spec::new(self.spec.read().clone()),
            owners: Owners::default(),
        }
    }
    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.__copy__()
    }
    fn __eq__(&self, other: &Bound<'_, PyAny>) -> bool {
        other.extract::<PyRef<'_, Self>>().is_ok_and(|other| {
            format!("{:?}", *self.spec.read()) == format!("{:?}", *other.spec.read())
        })
    }
    fn __repr__(&self) -> String {
        format!("ChartAxis({:?})", *self.spec.read())
    }
}

#[pyclass(name = "ChartDataset", module = "xnano_core._xnano_core")]
pub struct PyChartDataset {
    pub spec: Shared<DatasetSpec>,
    owners: Owners,
}
#[pymethods]
impl PyChartDataset {
    #[new]
    #[pyo3(signature = (*, name = None, data = None, marker = None, graph_type = None, style = None, fill_to_y = None))]
    fn new(
        name: Option<&Bound<'_, PyAny>>,
        data: Option<&Bound<'_, PyAny>>,
        marker: Option<&Bound<'_, PyAny>>,
        graph_type: Option<&Bound<'_, PyAny>>,
        style: Option<&Bound<'_, PyAny>>,
        fill_to_y: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        let mut spec = DatasetSpec::default();
        if let Some(value) = present(name) {
            spec.name = present(Some(value)).map(dynamic_string).transpose()?;
        }
        if let Some(value) = present(data) {
            spec.data = coordinates_arg(value)?;
        }
        if let Some(value) = present(marker) {
            spec.marker = marker_arg(value)?;
        }
        if let Some(value) = present(graph_type) {
            spec.graph_type = graph_type_arg(value)?;
        }
        if let Some(value) = present(style) {
            spec.style = style_spec_arg(Some(value))?;
        }
        if let Some(value) = present(fill_to_y) {
            spec.fill_to_y = dynamic_f64(value)?;
        }
        Ok(Self {
            spec: Spec::new(spec),
            owners: Owners::default(),
        })
    }
    #[getter]
    fn name<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let _ = py;
        optional_out(py, self.spec.read().name.as_ref(), string_out)
    }
    #[setter]
    fn set_name(&self, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let setting = present(value).map(dynamic_string).transpose()?;
        self.spec.edit(|spec| spec.name = setting);
        self.owners.repaint();
        Ok(())
    }
    #[getter]
    fn data(&self, py: Python<'_>) -> PyResult<Vec<(f64, f64)>> {
        let _ = py;
        Ok(self.spec.read().data.clone())
    }
    #[setter]
    fn set_data(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting = coordinates_arg(value)?;
        self.spec.edit(|spec| spec.data = setting);
        self.owners.repaint();
        Ok(())
    }
    #[getter]
    fn marker<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let _ = py;
        string_out(py, &self.spec.read().marker)
    }
    #[setter]
    fn set_marker(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting = marker_arg(value)?;
        self.spec.edit(|spec| spec.marker = setting);
        self.owners.repaint();
        Ok(())
    }
    #[getter]
    fn graph_type<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let _ = py;
        string_out(py, &self.spec.read().graph_type)
    }
    #[setter]
    fn set_graph_type(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting = graph_type_arg(value)?;
        self.spec.edit(|spec| spec.graph_type = setting);
        self.owners.repaint();
        Ok(())
    }
    #[getter]
    fn style(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let _ = py;
        style_spec_to_py(py, &self.spec.read().style)
    }
    #[setter]
    fn set_style(&self, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let setting = style_spec_arg(value)?;
        self.spec.edit(|spec| spec.style = setting);
        self.owners.repaint();
        Ok(())
    }
    #[getter]
    fn fill_to_y<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let _ = py;
        crate::widgets::canvas::float_out(py, &self.spec.read().fill_to_y)
    }
    #[setter]
    fn set_fill_to_y(&self, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let setting = dynamic_f64(value)?;
        self.spec.edit(|spec| spec.fill_to_y = setting);
        self.owners.repaint();
        Ok(())
    }
    fn __copy__(&self) -> Self {
        Self {
            spec: Spec::new(self.spec.read().clone()),
            owners: Owners::default(),
        }
    }
    fn __deepcopy__(&self, _memo: &Bound<'_, PyAny>) -> Self {
        self.__copy__()
    }
    fn __eq__(&self, other: &Bound<'_, PyAny>) -> bool {
        other.extract::<PyRef<'_, Self>>().is_ok_and(|other| {
            format!("{:?}", *self.spec.read()) == format!("{:?}", *other.spec.read())
        })
    }
    fn __repr__(&self) -> String {
        format!("ChartDataset({:?})", *self.spec.read())
    }
}

#[pyclass(name = "Chart", module = "xnano_core._xnano_core", extends = PyWidget, subclass)]
pub struct PyChart {
    spec: Shared<ChartSpec>,
    datasets: Vec<Py<PyChartDataset>>,
    x_axis: Py<PyChartAxis>,
    y_axis: Py<PyChartAxis>,
    block: Option<Py<PyAny>>,
}
impl PyChart {
    fn refresh(slf: &Bound<'_, Self>) {
        repaint(&slf.as_super().as_super().as_super().borrow().core);
    }
}
#[pymethods]
impl PyChart {
    #[new]
    #[pyo3(signature = (datasets = None, *, x_axis = None, y_axis = None, style = None, legend_position = None, block = None, width = None, height = None, x = 0, y = 0))]
    fn new(
        py: Python<'_>,
        datasets: Option<&Bound<'_, PyAny>>,
        x_axis: Option<Py<PyChartAxis>>,
        y_axis: Option<Py<PyChartAxis>>,
        style: Option<&Bound<'_, PyAny>>,
        legend_position: Option<&Bound<'_, PyAny>>,
        block: Option<&Bound<'_, PyAny>>,
        width: Option<i32>,
        height: Option<i32>,
        x: i32,
        y: i32,
    ) -> PyResult<PyClassInitializer<Self>> {
        let datasets = present(datasets)
            .map(|values| {
                values
                    .try_iter()?
                    .map(|item| item?.extract().map_err(Into::into))
                    .collect::<PyResult<Vec<Py<PyChartDataset>>>>()
            })
            .transpose()?
            .unwrap_or_default();
        let x_axis = match x_axis {
            Some(axis) => axis,
            None => Py::new(py, PyChartAxis::new(None, None, None, None, None)?)?,
        };
        let y_axis = match y_axis {
            Some(axis) => axis,
            None => Py::new(py, PyChartAxis::new(None, None, None, None, None)?)?,
        };
        let spec = Spec::new(ChartSpec {
            datasets: datasets
                .iter()
                .map(|dataset| Arc::clone(&dataset.borrow(py).spec))
                .collect(),
            x_axis: Arc::clone(&x_axis.borrow(py).spec),
            y_axis: Arc::clone(&y_axis.borrow(py).spec),
            style: style_spec_arg(style)?,
            legend_position: present(legend_position).map(dynamic_string).transpose()?,
            hidden_legend_limits: None,
            block: block_arg(block)?,
        });
        let (initializer, core) = widget_with_core(
            Arc::clone(&spec),
            Frame {
                width,
                height,
                x,
                y,
            },
            (40, 12),
        )?;
        for dataset in &datasets {
            dataset.borrow(py).owners.add(&core);
        }
        x_axis.borrow(py).owners.add(&core);
        y_axis.borrow(py).owners.add(&core);
        repaint(&core);
        Ok(initializer.add_subclass(Self {
            spec,
            datasets,
            x_axis,
            y_axis,
            block: present(block).map(|value| value.clone().unbind()),
        }))
    }
    #[getter]
    fn datasets(&self, py: Python<'_>) -> Vec<Py<PyChartDataset>> {
        self.datasets
            .iter()
            .map(|dataset| dataset.clone_ref(py))
            .collect()
    }
    #[setter]
    fn set_datasets(slf: &Bound<'_, Self>, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let datasets = value
            .try_iter()?
            .map(|item| item?.extract().map_err(Into::into))
            .collect::<PyResult<Vec<Py<PyChartDataset>>>>()?;
        let core = Arc::clone(&slf.as_super().as_super().as_super().borrow().core);
        for dataset in &datasets {
            dataset.borrow(slf.py()).owners.add(&core);
        }
        slf.borrow().spec.edit(|spec| {
            spec.datasets = datasets
                .iter()
                .map(|dataset| Arc::clone(&dataset.borrow(slf.py()).spec))
                .collect();
        });
        slf.borrow_mut().datasets = datasets;
        Self::refresh(slf);
        Ok(())
    }
    #[getter]
    fn x_axis(&self, py: Python<'_>) -> Py<PyChartAxis> {
        self.x_axis.clone_ref(py)
    }
    #[setter]
    fn set_x_axis(slf: &Bound<'_, Self>, value: Py<PyChartAxis>) {
        value
            .borrow(slf.py())
            .owners
            .add(&slf.as_super().as_super().as_super().borrow().core);
        slf.borrow()
            .spec
            .edit(|spec| spec.x_axis = Arc::clone(&value.borrow(slf.py()).spec));
        slf.borrow_mut().x_axis = value;
        Self::refresh(slf);
    }
    #[getter]
    fn y_axis(&self, py: Python<'_>) -> Py<PyChartAxis> {
        self.y_axis.clone_ref(py)
    }
    #[setter]
    fn set_y_axis(slf: &Bound<'_, Self>, value: Py<PyChartAxis>) {
        value
            .borrow(slf.py())
            .owners
            .add(&slf.as_super().as_super().as_super().borrow().core);
        slf.borrow()
            .spec
            .edit(|spec| spec.y_axis = Arc::clone(&value.borrow(slf.py()).spec));
        slf.borrow_mut().y_axis = value;
        Self::refresh(slf);
    }
    #[getter]
    fn style(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        style_spec_to_py(py, &self.spec.read().style)
    }
    #[setter]
    fn set_style(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let style = style_spec_arg(value)?;
        slf.borrow().spec.edit(|spec| spec.style = style);
        Self::refresh(slf);
        Ok(())
    }
    #[getter]
    fn legend_position<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        optional_out(py, self.spec.read().legend_position.as_ref(), string_out)
    }
    #[setter]
    fn set_legend_position(
        slf: &Bound<'_, Self>,
        value: Option<&Bound<'_, PyAny>>,
    ) -> PyResult<()> {
        let position = present(value).map(dynamic_string).transpose()?;
        slf.borrow()
            .spec
            .edit(|spec| spec.legend_position = position);
        Self::refresh(slf);
        Ok(())
    }
    #[getter]
    fn block(&self, py: Python<'_>) -> Option<Py<PyAny>> {
        self.block.as_ref().map(|block| block.clone_ref(py))
    }
    #[setter]
    fn set_block(slf: &Bound<'_, Self>, value: Option<&Bound<'_, PyAny>>) -> PyResult<()> {
        let block = block_arg(value)?;
        slf.borrow().spec.edit(|spec| spec.block = block);
        slf.borrow_mut().block = present(value).map(|value| value.clone().unbind());
        Self::refresh(slf);
        Ok(())
    }
    fn __repr__(&self) -> String {
        format!("Chart(datasets={})", self.datasets.len())
    }
}
pub fn register(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<PyChartAxis>()?;
    module.add_class::<PyChartDataset>()?;
    module.add_class::<PyChart>()
}
