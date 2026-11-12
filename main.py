set_website_title("Material Finder")
set_site_information(
    author="Maxwell Hankey",
    description="Find's a material based on constraints you give",
    sources="None",
    planning=["Final CISC106 Brainstorming Sheets.pdf", "Material_Finder_LLM_Conversation (1).pdf"],
    links=["https://github.com/Mhankey-cyber/Material-Finder"]
)
hide_debug_information()
set_website_framed(False)
"""
Material Finder
===============

A Drafter website that helps a user pick a construction / engineering material.

The user enters five constraints for their object:
    1. Maximum weight (lbs)
    2. Maximum budget (dollars)
    3. Volume of material needed (cubic feet)
    4. Stress the object must withstand (psi)
    5. Project location (which sets temperature range and wet/dry weather)

The site checks every material in its catalog against all five constraints.
  * If one material works, it is returned.
  * If several materials work, all of them are listed (cheapest first) and the
    site says that any of them could work.
  * If none work, the site says it cannot find a suitable material.

Simplifications (this is a school project, not an engineering tool):
  * "Strength" is a single rough number in psi (pounds per square inch) for each
    material, standing in for the stress at which it bends or breaks.
  * Material weight = density * volume.
  * Material cost   = weight * cost per pound.

The site uses no advanced coding techniques beyond what was covered in class.
"""

from dataclasses import dataclass
from drafter import *

# ---------------------------------------------------------------------------
# Constants (global constants are allowed; they are never changed)
# ---------------------------------------------------------------------------

WET_WEATHER = "Wet"
DRY_WEATHER = "Dry"
NO_MATCH_MESSAGE = "Cannot find suitable material."


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ProjectSite:
    """A place where the object will be used.

    Attributes:
        name: Display name of the site, such as "Hot Desert".
        average_temperature: Typical temperature at the site in degrees Fahrenheit.
        weather: Either WET_WEATHER or DRY_WEATHER.
    """
    name: str
    average_temperature: int
    weather: str


@dataclass
class Material:
    """A material the website can recommend.

    Attributes:
        name: Name of the material.
        density: Density in pounds per cubic foot.
        cost_per_pound: Price in dollars per pound.
        is_water_resistant: True if the material survives constant moisture.
        strength: Approximate stress in psi the material can take before it
            bends or breaks.
        min_temperature: Lowest safe temperature in degrees Fahrenheit.
        max_temperature: Highest safe temperature in degrees Fahrenheit.
    """
    name: str
    density: float
    cost_per_pound: float
    is_water_resistant: bool
    strength: int
    min_temperature: int
    max_temperature: int


@dataclass
class SearchRecord:
    """A short record of one past search, shown on the history page.

    Attributes:
        constraints_summary: One-line description of the constraints used.
        outcome: Names of the matching materials, or the no-match message.
    """
    constraints_summary: str
    outcome: str


@dataclass
class State:
    """Everything the website remembers between pages.

    Attributes:
        materials: The full catalog of materials the site can recommend.
        max_weight: Heaviest the finished object may be, in pounds.
        max_cost: Most the user can spend on material, in dollars.
        volume: Volume of material needed, in cubic feet.
        required_strength: Stress the object must withstand, in psi.
        site: The project site (temperature and weather) chosen by the user.
        matches: Materials that satisfied every constraint in the latest search.
        history: Records of every search made during this visit.
    """
    materials: list[Material]
    max_weight: float
    max_cost: float
    volume: float
    required_strength: int
    site: ProjectSite
    matches: list[Material]
    history: list[SearchRecord]


# ---------------------------------------------------------------------------
# Constant data: site choices
# ---------------------------------------------------------------------------

SITE_OPTIONS = [
    ProjectSite("Arctic Tundra", -20, DRY_WEATHER),
    ProjectSite("Alpine Mountains", 25, WET_WEATHER),
    ProjectSite("Temperate Forest", 50, WET_WEATHER),
    ProjectSite("Temperate Plains", 55, DRY_WEATHER),
    ProjectSite("Coastal Salt Air", 65, WET_WEATHER),
    ProjectSite("Tropical Rainforest", 85, WET_WEATHER),
    ProjectSite("Hot Desert", 105, DRY_WEATHER),
]


# ---------------------------------------------------------------------------
# Helper functions (not routes)
# ---------------------------------------------------------------------------

def build_material_catalog() -> list[Material]:
    """Create the list of 20 materials the website can recommend.

    Values are rounded, typical figures meant for a class project.

    Returns:
        A new list containing 20 Material instances.
    """
    return [
        Material("Structural Steel", 490.0, 0.50, False, 36000, -20, 800),
        Material("Stainless Steel", 500.0, 2.00, True, 31000, -300, 1500),
        Material("Aluminum 6061", 169.0, 1.50, True, 40000, -320, 400),
        Material("Titanium Alloy", 277.0, 25.00, True, 120000, -320, 800),
        Material("Copper", 559.0, 4.50, True, 10000, -320, 400),
        Material("Brass", 530.0, 3.50, True, 25000, -320, 400),
        Material("Cast Iron", 450.0, 0.40, False, 30000, -40, 750),
        Material("Red Oak Wood", 44.0, 1.00, False, 14000, -40, 300),
        Material("Douglas Fir Wood", 34.0, 0.60, False, 12000, -40, 300),
        Material("Pressure-Treated Pine", 36.0, 0.40, True, 8000, -40, 250),
        Material("Concrete", 150.0, 0.05, True, 4000, -50, 600),
        Material("Reinforced Concrete", 155.0, 0.10, True, 6000, -50, 600),
        Material("Granite", 165.0, 0.30, True, 15000, -50, 1000),
        Material("HDPE Plastic", 60.0, 1.00, True, 4000, -148, 176),
        Material("PVC Plastic", 87.0, 0.80, True, 7500, 14, 140),
        Material("Polycarbonate", 75.0, 2.50, True, 9000, -40, 250),
        Material("Acrylic", 74.0, 2.00, True, 10000, -40, 170),
        Material("Nylon", 71.0, 2.50, True, 11000, -40, 250),
        Material("Carbon Fiber Composite", 98.0, 30.00, True, 100000, -60, 250),
        Material("Fiberglass", 112.0, 3.00, True, 30000, -60, 300),
    ]


def is_positive_number(text: str) -> bool:
    """Check whether text is a positive number such as "12" or "3.5".

    Args:
        text: The raw text a user typed into a TextBox.

    Returns:
        True if the text is a number greater than zero, otherwise False.
    """
    cleaned_text = text.strip()
    # Remove at most one decimal point so "3.5" counts as a number but "3.5.1" does not.
    digits_only = cleaned_text.replace(".", "", 1)
    if not digits_only.isdigit():
        return False
    return float(cleaned_text) > 0


def find_site_by_name(site_name: str) -> ProjectSite:
    """Look up a ProjectSite from the list of site options by its name.

    Args:
        site_name: Name of a site, taken from the location SelectBox.

    Returns:
        The matching ProjectSite, or the first option if no name matches.
    """
    for site in SITE_OPTIONS:
        if site.name == site_name:
            return site
    return SITE_OPTIONS[0]


def calculate_weight(material: Material, volume: float) -> float:
    """Calculate how much a volume of a material weighs.

    Args:
        material: The material being used.
        volume: Volume of material in cubic feet.

    Returns:
        Weight in pounds.
    """
    return material.density * volume


def calculate_cost(material: Material, volume: float) -> float:
    """Calculate how much a volume of a material costs.

    Args:
        material: The material being used.
        volume: Volume of material in cubic feet.

    Returns:
        Total cost in dollars.
    """
    return calculate_weight(material, volume) * material.cost_per_pound


def find_failed_constraints(material: Material, state: State) -> list[str]:
    """Check one material against all five of the user's constraints.

    Args:
        material: The material to test.
        state: The current State holding the user's constraints.

    Returns:
        A list of short messages, one for each constraint the material fails.
        An empty list means the material satisfies every constraint.
    """
    failed_constraints = []

    # Constraint 1: weight
    if calculate_weight(material, state.volume) > state.max_weight:
        failed_constraints.append("too heavy")

    # Constraint 2: cost
    if calculate_cost(material, state.volume) > state.max_cost:
        failed_constraints.append("too expensive")

    # Constraint 3: stress
    if material.strength < state.required_strength:
        failed_constraints.append("not strong enough")

    # Constraint 4: weather (wet sites need a water resistant material)
    if state.site.weather == WET_WEATHER and not material.is_water_resistant:
        failed_constraints.append("not water resistant")

    # Constraint 5: temperature (site must be inside the material's safe range)
    if state.site.average_temperature < material.min_temperature:
        failed_constraints.append("too cold for this material")
    elif state.site.average_temperature > material.max_temperature:
        failed_constraints.append("too hot for this material")

    return failed_constraints


def sort_materials_by_cost(materials: list[Material],
                           volume: float) -> list[Material]:
    """Put materials in order from cheapest to most expensive.

    Works by repeating one simple step: find the cheapest material that is
    still left in the list, move it to the end of the sorted list, and repeat
    until no materials are left.

    Args:
        materials: The materials to sort. This list is emptied by the function.
        volume: Volume of material in cubic feet, used to calculate each cost.

    Returns:
        A new list with the same materials, cheapest first.
    """
    sorted_materials = []
    while len(materials) > 0:
        cheapest_material = materials[0]
        for material in materials:
            if (calculate_cost(material, volume)
                    < calculate_cost(cheapest_material, volume)):
                cheapest_material = material
        sorted_materials.append(cheapest_material)
        materials.remove(cheapest_material)
    return sorted_materials


def search_materials(state: State) -> None:
    """Find every material that satisfies the constraints and store the results.

    Loops over the catalog in ``state.materials``, keeps the materials that fail
    no constraint, sorts them from cheapest to most expensive, and saves them in
    ``state.matches``. A SearchRecord is also added to ``state.history``.

    Args:
        state: The current State. Its ``matches`` and ``history`` are modified.
    """
    found_materials = []
    for material in state.materials:
        if len(find_failed_constraints(material, state)) == 0:
            found_materials.append(material)

    found_materials = sort_materials_by_cost(found_materials, state.volume)
    state.matches = found_materials

    if len(found_materials) == 0:
        outcome = NO_MATCH_MESSAGE
    else:
        outcome = ", ".join([material.name for material in found_materials])
    state.history.append(SearchRecord(describe_constraints(state), outcome))


def describe_constraints(state: State) -> str:
    """Build a one-line summary of the user's current constraints.

    Args:
        state: The current State.

    Returns:
        Text such as "Weight <= 500.0 lbs, Cost <= $200.0, ...".
    """
    # round(number, 2) keeps at most 2 decimal places, and str() turns a
    # number into text so it can be joined to other text with +.
    weight_text = "Weight <= " + str(round(state.max_weight, 2)) + " lbs"
    cost_text = "Cost <= $" + str(round(state.max_cost, 2))
    volume_text = "Volume = " + str(round(state.volume, 2)) + " cu ft"
    stress_text = "Stress = " + str(state.required_strength) + " psi"
    location_text = "Location = " + state.site.name

    summary = (weight_text + ", " + cost_text + ", " + volume_text + ", "
               + stress_text + ", " + location_text)
    return summary


def text_for_default(number: float) -> str:
    """Turn a stored number into text for a TextBox, or blank if not set yet.

    Args:
        number: A stored constraint value (0 means "not entered yet").

    Returns:
        The number as text, or an empty string if the number is zero.
    """
    if number == 0:
        return ""
    return str(number)


def build_constraint_page(state: State, message: str) -> Page:
    """Build the page where the user enters all five constraints.

    Args:
        state: The current State (used to pre-fill the input fields).
        message: An error message to show at the top, or "" for none.

    Returns:
        The constraint input Page.
    """
    return Page(state, [
        Header("Enter Your Constraints"),
        message,
        "Maximum weight of the object (lbs):",
        TextBox("weight_text", text_for_default(state.max_weight)),
        "Maximum budget for material (dollars):",
        TextBox("cost_text", text_for_default(state.max_cost)),
        "Volume of material needed (cubic feet):",
        TextBox("volume_text", text_for_default(state.volume)),
        "Stress the object must withstand (psi):",
        TextBox("stress_text", text_for_default(state.required_strength)),
        "Project location:",
        SelectBox("location_name",
                  [site.name for site in SITE_OPTIONS],
                  state.site.name),
        LineBreak(),
        Button("Find Material", find_material),
        Button("Back to Home", index),
    ])


def build_results_page(state: State, message: str) -> Page:
    """Build the page that shows the constraints, the chosen material(s), and
    the controls for changing any single constraint.

    Args:
        state: The current State, including the latest ``matches``.
        message: An error message to show at the top, or "" for none.

    Returns:
        The results Page.
    """
    # Part 1: the user's constraints
    # Turn each value into text first, so each row is easy to read below.
    weight_text = str(round(state.max_weight, 2)) + " lbs"
    cost_text = "$" + str(round(state.max_cost, 2))
    volume_text = str(round(state.volume, 2)) + " cubic feet"
    stress_text = str(state.required_strength) + " psi"
    location_text = (state.site.name + " (" +
                     str(state.site.average_temperature) + " F, " +
                     state.site.weather + ")")

    # Each row of the table is a list with two items: a label and a value.
    # The first row is the table's column headings.
    constraint_rows = []
    constraint_rows.append(["Constraint", "Your Value"])
    constraint_rows.append(["Maximum weight", weight_text])
    constraint_rows.append(["Maximum cost", cost_text])
    constraint_rows.append(["Volume", volume_text])
    constraint_rows.append(["Stress", stress_text])
    constraint_rows.append(["Location", location_text])

    # Part 2: the outcome
    outcome_content = []
    if len(state.matches) == 0:
        outcome_content.append(Header(NO_MATCH_MESSAGE, 2))
        outcome_content.append("Try raising the budget or weight limit, "
                               "lowering the stress, or changing the location.")
    else:
        if len(state.matches) == 1:
            outcome_content.append(Header("Best Material", 2))
            outcome_content.append(state.matches[0].name + " is the only "
                                   "material that meets all your constraints.")
        else:
            outcome_content.append(Header("Suitable Materials", 2))
            outcome_content.append(str(len(state.matches)) +
                                   " materials meet all your constraints, so "
                                   "any of them could work. They are listed "
                                   "cheapest first.")

        match_rows = [["Material", "Weight (lbs)", "Total Cost",
                       "Strength (psi)"]]
        for material in state.matches:
            weight_text = str(round(calculate_weight(material, state.volume), 2))
            cost_text = "$" + str(round(calculate_cost(material, state.volume), 2))
            strength_text = str(material.strength)
            match_rows.append([material.name, weight_text, cost_text,
                               strength_text])
        outcome_content.append(Table(match_rows))

    # Part 3: controls for changing one constraint at a time
    return Page(state, [
        Header("Your Results"),
        message,
        Header("Your Constraints", 2),
        Table(constraint_rows),
        *outcome_content,
        HorizontalRule(),
        Header("Change One Constraint", 2),
        "New maximum weight (lbs):",
        TextBox("new_weight", ""),
        Button("Change Weight", change_weight),
        LineBreak(),
        "New maximum cost (dollars):",
        TextBox("new_cost", ""),
        Button("Change Cost", change_cost),
        LineBreak(),
        "New volume (cubic feet):",
        TextBox("new_volume", ""),
        Button("Change Volume", change_volume),
        LineBreak(),
        "New stress (psi):",
        TextBox("new_stress", ""),
        Button("Change Stress", change_stress),
        LineBreak(),
        "New location:",
        SelectBox("new_location",
                  [site.name for site in SITE_OPTIONS],
                  state.site.name),
        Button("Change Location", change_location),
        HorizontalRule(),
        Button("Start New Search", new_search),
        Button("Back to Home", index),
    ])


# ---------------------------------------------------------------------------
# Routes / pages
# ---------------------------------------------------------------------------

@route
def index(state: State) -> Page:
    """Home page: links to the instructions, a new search, and the lists.

    Args:
        state: The current State.

    Returns:
        The home Page.
    """
    return Page(state, [
        Header("Material Finder"),
        "Tell us about your object and where it will be used, and we will "
        "find the materials that fit.",
        LineBreak(),
        Button("Instructions", instructions_page),
        Button("Find a Material", constraint_page),
        Button("See All Materials", materials_page),
        Button("Past Searches", history_page),
    ])


@route
def instructions_page(state: State) -> Page:
    """Instructions page: explains each input and how the matching works.

    Args:
        state: The current State.

    Returns:
        The instructions Page.
    """
    return Page(state, [
        Header("Instructions"),
        "Fill in all five constraints. Numbers must be positive and contain "
        "only digits and at most one decimal point (no units or commas).",
        BulletedList([
            "Maximum weight: the heaviest the finished object can be, in pounds.",
            "Maximum cost: the most you can spend on the material, in dollars.",
            "Volume: how much material you need, in cubic feet.",
            "Stress: how much force per square inch the object must handle "
            "(psi). Whole numbers only.",
            "Location: pick where the object will be used. Wet locations need "
            "water resistant materials, and the material must be safe at "
            "the location's temperature.",
        ]),
        "A material is only suggested if it meets every constraint. If more "
        "than one material works, all of them are shown and any could work. "
        "If none work, you will be told no suitable material was found.",
        "On the results page you can change one constraint at a time to see "
        "how it affects the answer.",
        LineBreak(),
        Button("Back to Home", index),
    ])


@route
def constraint_page(state: State) -> Page:
    """Constraint input page: where the user enters the first set of constraints.

    Args:
        state: The current State.

    Returns:
        The constraint input Page.
    """
    return build_constraint_page(state, "")


@route
def find_material(state: State, weight_text: str, cost_text: str,
                  volume_text: str, stress_text: str,
                  location_name: str) -> Page:
    """Validate all five constraints, save them, and search for materials.

    Args:
        state: The current State. All five constraint fields are modified.
        weight_text: Text from the maximum weight TextBox.
        cost_text: Text from the maximum cost TextBox.
        volume_text: Text from the volume TextBox.
        stress_text: Text from the stress TextBox.
        location_name: Name chosen in the location SelectBox.

    Returns:
        The results Page if every input is valid, otherwise the constraint
        input Page with an error message.
    """
    if not is_positive_number(weight_text):
        return build_constraint_page(state, "Weight must be a positive number.")
    if not is_positive_number(cost_text):
        return build_constraint_page(state, "Cost must be a positive number.")
    if not is_positive_number(volume_text):
        return build_constraint_page(state, "Volume must be a positive number.")
    if not stress_text.strip().isdigit() or int(stress_text) <= 0:
        return build_constraint_page(state,
                                     "Stress must be a positive whole number.")

    state.max_weight = float(weight_text)
    state.max_cost = float(cost_text)
    state.volume = float(volume_text)
    state.required_strength = int(stress_text)
    state.site = find_site_by_name(location_name)

    search_materials(state)
    return build_results_page(state, "")


@route
def materials_page(state: State) -> Page:
    """List page: shows every material in the catalog.

    Args:
        state: The current State (its ``materials`` list is displayed).

    Returns:
        The catalog Page.
    """
    catalog_rows = [["Material", "Density (lb/cu ft)", "Cost ($/lb)",
                     "Water Resistant", "Strength (psi)", "Safe Temp (F)"]]
    for material in state.materials:
        if material.is_water_resistant:
            water_text = "Yes"
        else:
            water_text = "No"
        density_text = str(material.density)
        cost_text = "$" + str(material.cost_per_pound)
        strength_text = str(material.strength)
        temperature_text = (str(material.min_temperature) + " to " +
                            str(material.max_temperature))
        catalog_rows.append([material.name, density_text, cost_text,
                             water_text, strength_text, temperature_text])
    return Page(state, [
        Header("All Materials"),
        "The site can recommend any of these " + str(len(state.materials)) +
        " materials.",
        Table(catalog_rows),
        LineBreak(),
        Button("Back to Home", index),
    ])


@route
def history_page(state: State) -> Page:
    """History page: shows every search made during this visit.

    Args:
        state: The current State (its ``history`` list is displayed).

    Returns:
        The history Page.
    """
    if len(state.history) == 0:
        history_content = ["You have not made any searches yet."]
    else:
        history_rows = [["#", "Constraints", "Result"]]
        search_number = 1
        for record in state.history:
            history_rows.append([str(search_number),
                                 record.constraints_summary,
                                 record.outcome])
            search_number += 1
        history_content = [Table(history_rows)]
    return Page(state, [
        Header("Past Searches"),
        *history_content,
        LineBreak(),
        Button("Back to Home", index),
    ])


@route
def change_weight(state: State, new_weight: str) -> Page:
    """Change only the maximum weight and search again.

    Args:
        state: The current State. ``max_weight`` is modified.
        new_weight: Text from the new weight TextBox.

    Returns:
        The updated results Page, or the unchanged results Page with an
        error message if the input was invalid.
    """
    if not is_positive_number(new_weight):
        return build_results_page(state, "Weight must be a positive number.")
    state.max_weight = float(new_weight)
    search_materials(state)
    return build_results_page(state, "")


@route
def change_cost(state: State, new_cost: str) -> Page:
    """Change only the maximum cost and search again.

    Args:
        state: The current State. ``max_cost`` is modified.
        new_cost: Text from the new cost TextBox.

    Returns:
        The updated results Page, or the unchanged results Page with an
        error message if the input was invalid.
    """
    if not is_positive_number(new_cost):
        return build_results_page(state, "Cost must be a positive number.")
    state.max_cost = float(new_cost)
    search_materials(state)
    return build_results_page(state, "")


@route
def change_volume(state: State, new_volume: str) -> Page:
    """Change only the volume and search again.

    Args:
        state: The current State. ``volume`` is modified.
        new_volume: Text from the new volume TextBox.

    Returns:
        The updated results Page, or the unchanged results Page with an
        error message if the input was invalid.
    """
    if not is_positive_number(new_volume):
        return build_results_page(state, "Volume must be a positive number.")
    state.volume = float(new_volume)
    search_materials(state)
    return build_results_page(state, "")


@route
def change_stress(state: State, new_stress: str) -> Page:
    """Change only the required stress and search again.

    Args:
        state: The current State. ``required_strength`` is modified.
        new_stress: Text from the new stress TextBox.

    Returns:
        The updated results Page, or the unchanged results Page with an
        error message if the input was invalid.
    """
    if not new_stress.strip().isdigit() or int(new_stress) <= 0:
        return build_results_page(state,
                                  "Stress must be a positive whole number.")
    state.required_strength = int(new_stress)
    search_materials(state)
    return build_results_page(state, "")


@route
def change_location(state: State, new_location: str) -> Page:
    """Change only the project location and search again.

    Args:
        state: The current State. ``site`` is modified.
        new_location: Name chosen in the new location SelectBox.

    Returns:
        The updated results Page.
    """
    state.site = find_site_by_name(new_location)
    search_materials(state)
    return build_results_page(state, "")


@route
def new_search(state: State) -> Page:
    """Clear the old constraints and send the user to enter new ones.

    The search history and the materials catalog are kept.

    Args:
        state: The current State. All constraints and ``matches`` are reset.

    Returns:
        The constraint input Page with blank fields.
    """
    state.max_weight = 0.0
    state.max_cost = 0.0
    state.volume = 0.0
    state.required_strength = 0
    state.matches = []
    return build_constraint_page(state, "")


# ---------------------------------------------------------------------------
# Start the website
# ---------------------------------------------------------------------------

start_server(State(
    materials=build_material_catalog(),
    max_weight=0.0,
    max_cost=0.0,
    volume=0.0,
    required_strength=0,
    site=SITE_OPTIONS[0],
    matches=[],
    history=[],
))
