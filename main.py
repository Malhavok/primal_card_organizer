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


class Card(NamedTuple):
    width: int
    height: int


class BoatParams(NamedTuple):
    boat_height: int = 76
    card_cover_front: float = 0.67
    card_cover_side: float = 0.5
    width_tolerance: int | float = 1
    depth_tolerance: int | float = 0.5
    rounding_radius: int = 5
    flap_length: int = 10
    flap_cut: int = 2
    internal_flap_ratio: float = 0.6

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
        with_cutouts: bool,
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

    if with_cutouts:
        path_drawer.draw_right_dash_and_back(full_card_width)

    path_drawer.draw_down(full_stack_depth)

    if with_cutouts:
        path_drawer.draw_right_dash_and_back(full_card_width)
        path_drawer.draw_down_dash_and_back(side_size)

    # First flap, supporting bottom.
    path_drawer.line_by(-boat_params.flap_cut, -boat_params.flap_length)
    path_drawer.draw_left(full_stack_depth - 2 * boat_params.flap_cut)
    path_drawer.line_by(-boat_params.flap_cut, boat_params.flap_length)

    if with_cutouts:
        path_drawer.draw_right_dash_and_back(full_stack_depth)
        path_drawer.draw_down_dash_and_back(side_size)

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

    if with_cutouts:
        path_drawer.draw_down_dash_and_back(side_size)

    # Fourth flap, catching bottom.
    path_drawer.line_by(-boat_params.flap_cut, -boat_params.flap_length)
    path_drawer.draw_left(full_stack_depth - 2 * boat_params.flap_cut)
    path_drawer.line_by(-boat_params.flap_cut, boat_params.flap_length)

    if with_cutouts:
        path_drawer.draw_right_dash_and_back(full_stack_depth)
        path_drawer.draw_down_dash_and_back(side_size)

    path_drawer.draw_up(full_stack_depth)
    path_drawer.draw_up(boat_params.boat_height - boat_params.rounding_radius)
    path_drawer.draw_arc(-boat_params.rounding_radius, -boat_params.rounding_radius, boat_params.rounding_radius)
    path_drawer.draw_left(full_card_width - 2 * boat_params.rounding_radius)

    path = drawing.path(d=path_drawer.get_draw_command(), fill="none", stroke="black", stroke_width=HAIRLINE_THIN)
    group.add(path)

    size_diff = boat_params.boat_height - card.height
    offset = 2
    box_size = size_diff - offset * 2
    bottom_image_size = int(front_size * 0.8)

    if image_path is not None:
        image_data = get_image_data(image_path)
        if with_cutouts:
            group.add(
                drawing.image(
                    image_data,
                    insert=(boat_params.flap_length + full_stack_depth + boat_params.rounding_radius, offset),
                    size=(box_size, box_size),
                )
            )
        else:
            image = drawing.image(
                image_data,
                insert=(
                    boat_params.flap_length + full_stack_depth + (full_card_width - bottom_image_size) / 2,
                    boat_params.boat_height + full_stack_depth + (front_size - bottom_image_size) / 2,
                ),
                size=(bottom_image_size, bottom_image_size),
            )
            image.rotate(180, center=(
                boat_params.flap_length + full_stack_depth + full_card_width / 2,
                boat_params.boat_height + full_stack_depth + front_size / 2,
            ))
            group.add(
                image
            )

    if text is not None and with_cutouts:
        image_offset = 0 if image_path is None else box_size
        group.add(
            drawing.text(
                text,
                insert=(
                    boat_params.flap_length + full_stack_depth + 2 * boat_params.rounding_radius + offset + image_offset,
                    offset + box_size,
                ),
                font_size=f'{box_size}pt',
                font_family="Katari",
                fill="black",
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
        with_cutouts: bool,
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
        with_cutouts=with_cutouts,
        image_path=image_path,
        text=text,
    )
    boat_data.group.translate((A4_WIDTH - boat_data.width) / 2, 20)
    drawing.add(boat_data.group)

    buffer = io.StringIO()
    drawing.write(buffer)
    cairosvg.svg2svg(buffer.getvalue(), write_to=str(output_file))


CARD_GENERIC = Card(88, 63)
GENERIC_PARAMS = BoatParams(boat_height=75)

CARD_RECT = Card(60, 60)
RECT_PARAMS = BoatParams(boat_height=71)


class ToCut(NamedTuple):
    filename: str
    card: Card
    params: BoatParams
    stack_depth: int
    image: pathlib.Path | None = None
    text: str | None = None
    with_internal_flaps: bool = False


def make_monster(name: str, stack_depth: int = 10) -> ToCut:
    image = pathlib.Path('./icons/monsters') / f'{name.lower()}.svg'
    if not image.exists():
        image = None
    return ToCut(
        filename=f'monster_{name}',
        card=CARD_GENERIC,
        params=GENERIC_PARAMS,
        stack_depth=stack_depth,
        image=image,
        text=None,
    )


def make_equip(image: str | None, text: str | None, stack_depth: int) -> ToCut:
    image_path = image and pathlib.Path('./icons/elements') / f'{image}.svg'
    return ToCut(
        filename=f'eq_{image or text}',
        card=CARD_RECT,
        params=RECT_PARAMS,
        stack_depth=stack_depth,
        image=image_path,
        text=text,
    )


MONSTERS = [
    make_monster('Vyraxen'),
    make_monster('Kharja'),
    make_monster('Toramat'),
    make_monster('Dygorax'),
    make_monster('Korowon'),
    make_monster('Felaxir'),
    make_monster('Morkraas'),
    make_monster('Jekoros'),
    make_monster('Hurom'),
    make_monster('Tarragua'),
    make_monster('Ozew', stack_depth=13),
    make_monster('Orouxen', stack_depth=15),
    make_monster('Awakened', stack_depth=14),
    make_monster('Great sword', stack_depth=18),
    make_monster('Great bow', stack_depth=18),
    make_monster('Hammer', stack_depth=18),
    make_monster('Sword and shield', stack_depth=18),
]

EQUIPMENT = [
    make_equip(equip_type, equip_type, stack_depth=17)
    for equip_type in [
        'Coral',
        'Fire',
        'Thunder',
        'Horn',
        'Metal',
        'Crystal',
    ]
]

RAW_EQUIPMENT = [
    make_equip(image=None, text='Rewards', stack_depth=14),
    make_equip(image=None, text='Base eq', stack_depth=3),
]

POTIONS = [
    make_equip('potion', text='Potions', stack_depth=25),
]

TO_CUT = MONSTERS + EQUIPMENT + RAW_EQUIPMENT + POTIONS


def handle_cut(cut_input: ToCut) -> None:
    for cutout, suffix in [(True, 'internal'), (False, 'external')]:
        file_path = pathlib.Path('./output') / f'{cut_input.filename}_{suffix}.svg'
        save_boat(
            file_path,
            with_cutouts=cutout,
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
