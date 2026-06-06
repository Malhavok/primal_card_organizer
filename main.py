import base64
import io
import math
import pathlib
from typing import (
    NamedTuple,
    Callable,
)

import cairosvg
import svgwrite
from svgwrite.container import Group as SVGGroup


def make_mm(value: int) -> str:
    return f'{value}mm'


A4_WIDTH = 210
A4_HEIGHT = 297
SIZE = (make_mm(A4_WIDTH), make_mm(A4_HEIGHT))
VIEW_BOX = f'{0} {0} {A4_WIDTH} {A4_HEIGHT}'
HAIRLINE_THIN = '0.25px'

ELEMENTS = [
    'Coral',
    'Fire',
    'Thunder',
    'Horn',
    'Metal',
    'Crystal',
    'Feather',
    'Ice',
    'Venom',
]


class Card(NamedTuple):
    width: int
    height: int


class BoatParams(NamedTuple):
    boat_height: int = 76
    card_cover_front: float = 0.67
    card_cover_side: float = 0.5
    width_tolerance: int | float = 1
    depth_tolerance: int | float = 1
    rounding_radius: int = 5
    flap_length: int = 10
    flap_cut: int = 2
    internal_flap_ratio: float = 0.6
    force_box_size: float | None = None

    def front_size(self, card_height: int) -> int:
        return int(math.ceil(card_height * self.card_cover_front))

    def side_size(self, card_height: int) -> int:
        return int(math.ceil(card_height * self.card_cover_side))


class PathDrawer:
    def __init__(self):
        self.commands = []

    def get_draw_command(self) -> str:
        return ' '.join(self.commands)

    def close(self) -> None:
        self.commands.append('Z')

    def move_to(self, x: int, y: int) -> None:
        self.commands.append(f'M {x} {y}')

    def move_by(self, dx: int, dy: int) -> None:
        self.commands.append(f'm {dx} {dy}')

    def line_to(self, x: int, y: int) -> None:
        self.commands.append(f'L {x} {y}')

    def line_by(self, dx: int, dy: int) -> None:
        self.commands.append(f'l {dx} {dy}')

    def draw_down(self, length: int) -> None:
        self.commands.append(f'v {length}')

    def draw_up(self, length: int) -> None:
        self.commands.append(f'v {-length}')

    def draw_left(self, length: int) -> None:
        self.commands.append(f'h {-length}')

    def draw_right(self, length: int) -> None:
        self.commands.append(f'h {length}')

    def draw_arc(self, end_x: int, end_y: int, radius: int, counter_clockwise: bool = True) -> None:
        self.commands.append(f'a {radius} {radius} 0 0 {0 if counter_clockwise else 1} {end_x} {end_y}')

    def draw_right_dash_and_back(self, length: int, dash_len: int = 1, stop_len: int = 1) -> None:
        self._make_dashes(self.draw_right, lambda x: self.move_by(x, 0), length, dash_len, stop_len)
        self.move_by(-length, 0)

    def draw_down_dash_and_back(self, length: int, dash_len: int = 1, stop_len: int = 1) -> None:
        self._make_dashes(self.draw_down, lambda x: self.move_by(0, x), length, dash_len, stop_len)
        self.move_by(0, -length)

    @classmethod
    def _make_dashes(
            cls,
            cut_fun: Callable[[int], None],
            step_fun: Callable[[int], None],
            length: int,
            dash_len: int,
            stop_len: int,
    ) -> None:
        step_fun(stop_len)

        # We have to start and end with a stop, so there's never 100% cut.
        remaining_length = max(0, length - 2 * stop_len)
        is_dash = True
        while remaining_length > 0:
            default_step_len = dash_len if is_dash else stop_len
            step_len = min(remaining_length, default_step_len)

            if is_dash:
                cut_fun(step_len)
            else:
                step_fun(step_len)

            remaining_length -= step_len
            is_dash = not is_dash

        step_fun(stop_len)


def get_image_data(filepath: pathlib.Path) -> str:
    data = base64.b64encode(filepath.read_bytes()).decode()
    return f'data:image/svg+xml;base64,{data}'


class DrawBoatData(NamedTuple):
    group: SVGGroup
    width: int
    height: int


def draw_boat(
        drawing: svgwrite.Drawing,
        card: Card,
        stack_depth: int,
        boat_params: BoatParams,
        image_path: pathlib.Path | None = None,
        text: str | None = None,
) -> DrawBoatData:
    full_card_width = card.width + boat_params.width_tolerance
    full_stack_depth = stack_depth + boat_params.depth_tolerance
    front_size = boat_params.front_size(card.height)
    side_size = boat_params.side_size(card.height)
    front_radius = front_size - side_size

    group = drawing.g()

    # Drawing outline of the whole box.
    #     0         1         2
    #     0123456789012345678901234
    #  0         /---------\
    #  1         |Title    |
    #  2         +---------+
    #  3         |  Back   |
    #  4         |         |
    #  5         +---------+
    #  6       /\| Bottom  |/\
    #  7     /+--+---------+--+\
    #  8    | |  |  Front  |  | |
    #  9     \+--|         |--+/
    # 10         +---------+
    path_drawer = PathDrawer()

    path_drawer.move_to(boat_params.flap_length + full_stack_depth + boat_params.rounding_radius, 0)

    path_drawer.draw_arc(-boat_params.rounding_radius, boat_params.rounding_radius, boat_params.rounding_radius)
    path_drawer.draw_down(boat_params.boat_height - boat_params.rounding_radius)

    path_drawer.draw_right_dash_and_back(full_card_width)

    path_drawer.draw_down(full_stack_depth)

    path_drawer.draw_right_dash_and_back(full_card_width)
    path_drawer.draw_down_dash_and_back(side_size)

    # First flap, supporting bottom.
    def flap_catching_bottom():
        path_drawer.line_by(-boat_params.flap_cut, -boat_params.flap_length)
        path_drawer.draw_left(full_stack_depth - 2 * boat_params.flap_cut)
        path_drawer.line_by(-boat_params.flap_cut, boat_params.flap_length)

        path_drawer.draw_right_dash_and_back(full_stack_depth)
        path_drawer.draw_down_dash_and_back(side_size)

    flap_catching_bottom()

    # Second flap, catching back.
    path_drawer.line_by(-boat_params.flap_length, boat_params.flap_cut)
    path_drawer.draw_down(side_size - boat_params.flap_cut * 2)
    path_drawer.line_by(boat_params.flap_length, boat_params.flap_cut)

    path_drawer.draw_right(full_stack_depth)
    path_drawer.draw_arc(front_radius, front_radius, front_radius)
    path_drawer.draw_right(full_card_width - 2 * front_radius)
    path_drawer.draw_arc(front_radius, -front_radius, front_radius)
    path_drawer.draw_right(full_stack_depth)

    # Third flap, catching back.
    path_drawer.line_by(boat_params.flap_length, -boat_params.flap_cut)
    path_drawer.draw_up(side_size - 2 * boat_params.flap_cut)
    path_drawer.line_by(-boat_params.flap_length, -boat_params.flap_cut)

    path_drawer.draw_down_dash_and_back(side_size)

    # Fourth flap, catching bottom.
    flap_catching_bottom()

    path_drawer.draw_up(full_stack_depth)
    path_drawer.draw_up(boat_params.boat_height - boat_params.rounding_radius)
    path_drawer.draw_arc(-boat_params.rounding_radius, -boat_params.rounding_radius, boat_params.rounding_radius)
    path_drawer.draw_left(full_card_width - 2 * boat_params.rounding_radius)

    path = drawing.path(d=path_drawer.get_draw_command(), fill="none", stroke="black", stroke_width=HAIRLINE_THIN)
    group.add(path)

    size_diff = boat_params.boat_height - card.height
    offset = 0.2
    box_size = boat_params.force_box_size or (size_diff - offset * 2)

    if image_path is not None:
        image_data = get_image_data(image_path)
        group.add(
            drawing.image(
                image_data,
                insert=(
                    boat_params.flap_length
                    + full_stack_depth
                    + boat_params.rounding_radius / 2
                    + card.width * 0 / 10,
                    offset
                ),
                size=(box_size, box_size),
            )
        )

    if text is not None:
        image_offset = card.width * 1.25 / 10 if image_path is not None else card.width * 1.25 / 10
        group.add(
            drawing.text(
                text,
                insert=(
                    boat_params.flap_length
                    + full_stack_depth
                    + boat_params.rounding_radius
                    + offset
                    + image_offset,
                    offset + box_size,
                ),
                font_size=f'{box_size}pt',
                font_family="Katari",
                fill="#1F1F1F",
                text_anchor="start",
            )
        )

    return DrawBoatData(
        group=group,
        width=full_card_width + 2 * full_stack_depth + 2 * boat_params.flap_length,
        height=boat_params.boat_height + full_stack_depth + front_size,
    )


def save_boat(
        output_file: pathlib.Path,
        card: Card,
        stack_depth: int,
        board_params: BoatParams,
        image_path: pathlib.Path | None = None,
        text: str | None = None,
) -> None:
    drawing = svgwrite.Drawing(
        filename='test',
        size=SIZE,
        viewBox=VIEW_BOX,
        profile='tiny',
    )

    boat_data = draw_boat(
        drawing=drawing,
        card=card,
        stack_depth=stack_depth,
        boat_params=board_params,
        image_path=image_path,
        text=text,
    )
    boat_data.group.translate((A4_WIDTH - boat_data.width) / 2, 20)
    drawing.add(boat_data.group)

    buffer = io.StringIO()
    drawing.write(buffer)
    cairosvg.svg2svg(buffer.getvalue(), write_to=str(output_file))


# CARD_ATTRITION = Card(66, 44)
CARD_ATTRITION = Card(44, 66)
ATTRITION_PARAMS = BoatParams(force_box_size=5)

CARD_GENERIC = Card(90, 65)
GENERIC_PARAMS = BoatParams(boat_height=75)

CARD_RECT = Card(63, 63)
RECT_PARAMS = BoatParams(boat_height=71)

CARD_LARGE = Card(123, 73)
LARGE_PARAMS = BoatParams(force_box_size=7)


class ToCut(NamedTuple):
    filename: str
    card: Card
    params: BoatParams
    stack_depth: int
    image: pathlib.Path | None = None
    text: str | None = None


def make_monster(name: str, stack_depth: int, force_no_image: bool = False) -> ToCut:
    image = pathlib.Path('./icons/monsters') / f'{name.lower()}.svg'
    if not image.exists() or force_no_image:
        image = None
    return ToCut(
        filename=f'monster_{name}',
        card=CARD_GENERIC,
        params=GENERIC_PARAMS,
        stack_depth=stack_depth,
        image=image,
        text=name,
    )


def make_equip(image: str | None, text: str | None, stack_depth: int) -> ToCut:
    image_path = image and pathlib.Path('./icons/elements') / f'{image}.svg'
    return ToCut(
        filename=f'eq_{image or text}_{text}',
        card=CARD_RECT,
        params=RECT_PARAMS,
        stack_depth=stack_depth,
        image=image_path,
        text=text,
    )


def make_weapon(image: str, text: str, stack_depth: int = 8) -> ToCut:
    image = pathlib.Path('./icons/elements') / f'{image.lower()}.svg'
    if not image.exists():
        image = None
    return ToCut(
        filename=f'weapon_{text}',
        card=CARD_LARGE,
        params=LARGE_PARAMS,
        stack_depth=stack_depth,
        image=image,
        text=text,
    )


DEFAULT_MONSTER = 26
MONSTERS = [
    make_monster(name='Vyraxen', stack_depth=DEFAULT_MONSTER),
    make_monster(name='Kharja', stack_depth=DEFAULT_MONSTER),
    make_monster(name='Toramat', stack_depth=DEFAULT_MONSTER),
    make_monster(name='Dygorax', stack_depth=DEFAULT_MONSTER),
    make_monster(name='Korowon', stack_depth=DEFAULT_MONSTER),
    make_monster(name='Felaxir', stack_depth=DEFAULT_MONSTER),
    make_monster(name='Morkraas', stack_depth=DEFAULT_MONSTER),
    make_monster(name='Jekoros', stack_depth=DEFAULT_MONSTER),
    make_monster(name='Hurom', stack_depth=DEFAULT_MONSTER),
    make_monster(name='Tarragua', stack_depth=DEFAULT_MONSTER),
    make_monster(name='Ozew', stack_depth=29),
    make_monster(name='Orouxen', stack_depth=44),
    make_monster(name='Awakened', stack_depth=39),

    make_monster(name='Pazis', stack_depth=43),
    make_monster(name='Nagarjas', stack_depth=DEFAULT_MONSTER),

    make_monster(name='Hydar', stack_depth=38),
    make_monster(name='Reikal', stack_depth=46),

    make_monster(name='Sirkaaj', stack_depth=DEFAULT_MONSTER),
    make_monster(name='Mamuraak', stack_depth=DEFAULT_MONSTER),

    make_monster(name='Zekath', stack_depth=DEFAULT_MONSTER),
    make_monster(name='Zekalith', stack_depth=DEFAULT_MONSTER),
    make_monster(name='Xitheros', stack_depth=30),
    make_monster(name='Taraska', stack_depth=DEFAULT_MONSTER),

    make_monster(name='Dareon', stack_depth=33, force_no_image=True),
    make_monster(name='Mirah', stack_depth=33, force_no_image=True),
    make_monster(name='Thoreg', stack_depth=33, force_no_image=True),
    make_monster(name='Ljonar', stack_depth=33, force_no_image=True),
    make_monster(name='Karah', stack_depth=33, force_no_image=True),
    make_monster(name='Heleren', stack_depth=33, force_no_image=True),
    make_monster(name='Zaraya', stack_depth=33, force_no_image=True),
    make_monster(name='Drusk', stack_depth=33, force_no_image=True),

    make_monster(name='Havoc', stack_depth=5),
]

EQUIPMENT = [
    make_equip(equip_type, f'{equip_type} {level}', stack_depth=12)
    for level in [1, 2, 3]
    for equip_type in ELEMENTS
]

RAW_EQUIPMENT = [
    make_equip(image=None, text='Rewards', stack_depth=39),
    make_equip(image=None, text='Base eq', stack_depth=7),
]

POTIONS = [
    make_equip('potion', text=f'Potion {level}', stack_depth=18)
    for level in [1, 2, 3]
]

WEAPON_SINGLE_ELEMENT_DEPTH = 14
WEAPON_REMAINING_DEPTH = 19

WEAPONS = [
              make_weapon(element, element, stack_depth=WEAPON_SINGLE_ELEMENT_DEPTH)
              for element in ELEMENTS
          ] + [
              make_weapon('<None>', 'Basic + Ancient + Help', stack_depth=WEAPON_REMAINING_DEPTH)
          ]

QUESTS_PACK_DEPTH = 29
ATTRITION_PLUS_OZEW_DEPTH = 19
PRIMORDIAL_DEPTH = 7

ATTRITION = [
    ToCut(
        filename='attrition_attrition',
        card=CARD_ATTRITION,
        params=ATTRITION_PARAMS,
        stack_depth=ATTRITION_PLUS_OZEW_DEPTH,
        image=None,
        text='Attrition',
    ),
    ToCut(
        filename='attrition_primordial',
        card=CARD_ATTRITION,
        params=ATTRITION_PARAMS,
        stack_depth=PRIMORDIAL_DEPTH,
        image=None,
        text='Blood',
    ),
    ToCut(
        filename='attrition_quest',
        card=CARD_ATTRITION,
        params=ATTRITION_PARAMS,
        stack_depth=QUESTS_PACK_DEPTH,
        image=None,
        text='Quests',
    ),
]

TO_CUT = MONSTERS + EQUIPMENT + RAW_EQUIPMENT + POTIONS + WEAPONS + ATTRITION


def handle_cut(cut_input: ToCut) -> None:
    file_path = pathlib.Path('./output') / f'{cut_input.filename}.svg'
    save_boat(
        file_path,
        card=cut_input.card,
        board_params=cut_input.params,
        stack_depth=cut_input.stack_depth,
        image_path=cut_input.image,
        text=cut_input.text,
    )


def main() -> None:
    for cut in TO_CUT:
        handle_cut(cut)


if __name__ == '__main__':
    main()
