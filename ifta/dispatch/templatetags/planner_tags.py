from django import template

from dispatch.planner_cells import events_for_loads_on_date, primary_load_for_cell

register = template.Library()


@register.inclusion_tag("dispatch/includes/planner_driver_day_cell.html")
def planner_day_cell(driver, wd, load_by_cell, unavailability_by_cell, can_manage_dispatch):
    d = wd["date"]
    key = f"{driver.pk}_{d.isoformat()}"
    loads = load_by_cell.get(key, [])
    primary = primary_load_for_cell(loads, d)
    cell = events_for_loads_on_date(loads, d)
    unavailable = unavailability_by_cell.get(key)
    return {
        "driver": driver,
        "wd": wd,
        "cell_loads": loads,
        "cell_load": {"load": primary, "cell": cell} if primary else None,
        "cell_key": key,
        "unavailable": unavailable,
        "can_manage_dispatch": can_manage_dispatch,
    }
