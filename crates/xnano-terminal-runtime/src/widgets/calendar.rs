//! The ratatui `Monthly` calendar: one month with styled dates.
//!
//! Maps to `ratatui::widgets::calendar::Monthly`.

use ratatui::widgets::calendar::{CalendarEventStore, Monthly};
use ratatui_core::layout::Rect;
use ratatui_core::style::Style;
use ratatui_core::widgets::Widget;
use time::{Date, Month};

use crate::dynamic::Dynamic;
use crate::expression::EvalError;
use crate::grid::Grid;
use crate::widgets::block::{BlockSpec, ResolvedBlock, resolve_optional};
use crate::widgets::style::StyleSpec;
use crate::widgets::{Resolver, Shared, WidgetSpec};

/// A calendar date as year, month (1 to 12) and day (1 to 31).
pub type DateParts = (i32, u8, u8);

/// Build a date, or explain why the numbers are not one.
pub fn make_date(year: i32, month: u8, day: u8) -> Result<Date, String> {
    let month_name = Month::try_from(month)
        .map_err(|_| format!("{month} is not a month; use a whole number from 1 to 12"))?;
    Date::from_calendar_date(year, month_name, day).map_err(|_| {
        format!("{year}-{month:02}-{day:02} is not a calendar date; check the day of the month")
    })
}

/// The settings of a calendar.
#[derive(Debug, Clone)]
pub struct CalendarSpec {
    pub year: Dynamic<i32>,
    pub month: Dynamic<u8>,
    pub day: Dynamic<u8>,
    /// Dates with their own style.
    pub events: Vec<(DateParts, StyleSpec)>,
    pub surrounding_style: Option<StyleSpec>,
    pub weekdays_header_style: Option<StyleSpec>,
    pub month_header_style: Option<StyleSpec>,
    pub default_style: StyleSpec,
    pub block: Option<Shared<BlockSpec>>,
}

#[derive(Debug)]
pub struct ResolvedCalendar {
    date: Date,
    events: Vec<(Date, Style)>,
    surrounding_style: Option<Style>,
    weekdays_header_style: Option<Style>,
    month_header_style: Option<Style>,
    default_style: Style,
    block: Option<ResolvedBlock>,
}

impl WidgetSpec for CalendarSpec {
    type Resolved = ResolvedCalendar;

    fn resolve(&self, resolver: &mut Resolver<'_>) -> Result<Self::Resolved, EvalError> {
        let date = make_date(
            resolver.get(&self.year)?,
            resolver.get(&self.month)?,
            resolver.get(&self.day)?,
        )
        .map_err(EvalError::Type)?;
        let mut events = Vec::with_capacity(self.events.len());
        for ((year, month, day), style) in &self.events {
            events.push((
                make_date(*year, *month, *day).map_err(EvalError::Type)?,
                style.resolve(resolver)?,
            ));
        }
        let optional_style = |style: &Option<StyleSpec>, resolver: &mut Resolver<'_>| {
            style
                .as_ref()
                .map(|style| style.resolve(resolver))
                .transpose()
        };
        Ok(ResolvedCalendar {
            date,
            events,
            surrounding_style: optional_style(&self.surrounding_style, resolver)?,
            weekdays_header_style: optional_style(&self.weekdays_header_style, resolver)?,
            month_header_style: optional_style(&self.month_header_style, resolver)?,
            default_style: self.default_style.resolve(resolver)?,
            block: resolve_optional(&self.block, resolver)?,
        })
    }

    fn draw(resolved: &Self::Resolved, grid: &mut Grid) {
        let mut store = CalendarEventStore::default();
        for (date, style) in &resolved.events {
            store.add(*date, *style);
        }
        let mut calendar = Monthly::new(resolved.date, store).default_style(resolved.default_style);
        if let Some(style) = resolved.surrounding_style {
            calendar = calendar.show_surrounding(style);
        }
        if let Some(style) = resolved.weekdays_header_style {
            calendar = calendar.show_weekdays_header(style);
        }
        if let Some(style) = resolved.month_header_style {
            calendar = calendar.show_month_header(style);
        }
        if let Some(block) = &resolved.block {
            calendar = calendar.block(block.to_widget());
        }
        let area = Rect::new(0, 0, grid.width(), grid.height());
        calendar.render(area, grid.buffer_mut());
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::expression::{Environment, PropertyId, Scalar};

    struct Offline;
    impl Environment for Offline {
        fn property(&self, id: PropertyId) -> Result<Scalar, EvalError> {
            Err(EvalError::RuntimeRequired(id.name().to_owned()))
        }
    }

    fn spec(year: i32, month: u8, day: u8) -> CalendarSpec {
        CalendarSpec {
            year: Dynamic::Fixed(year),
            month: Dynamic::Fixed(month),
            day: Dynamic::Fixed(day),
            events: Vec::new(),
            surrounding_style: None,
            weekdays_header_style: Some(StyleSpec::default()),
            month_header_style: Some(StyleSpec::default()),
            default_style: StyleSpec::default(),
            block: None,
        }
    }

    #[test]
    fn a_calendar_shows_its_month() {
        let resolved = spec(2024, 2, 14)
            .resolve(&mut Resolver::new(&Offline))
            .unwrap();
        let mut grid = Grid::new(24, 10);
        CalendarSpec::draw(&resolved, &mut grid);
        let text = grid.text_rows().join("\n");
        assert!(text.contains("February 2024"), "{text}");
        assert!(text.contains("29"), "{text}");
    }

    #[test]
    fn impossible_dates_explain_themselves() {
        let error = spec(2023, 2, 30)
            .resolve(&mut Resolver::new(&Offline))
            .unwrap_err();
        assert!(error.to_string().contains("not a calendar date"));
        let error = spec(2023, 13, 1)
            .resolve(&mut Resolver::new(&Offline))
            .unwrap_err();
        assert!(error.to_string().contains("1 to 12"));
    }
}
