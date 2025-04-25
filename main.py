import base64
import io
import math
import pathlib
from typing import NamedTuple

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
    tolerance: int = 1
    rounding_radius: int = 5
    flap_length: int = 10
    flap_cut: int = 2

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

    def move(self, x: int, y: int) -> None:
        self.commands.append(f'M {x} {y}')

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


def get_image_data(filepath: pathlib.Path) -> str:
    data = base64.b64encode(filepath.read_bytes()).decode()
    return f'data:image/svg+xml;base64,{data}'


def draw_boat(
        drawing: svgwrite.Drawing,
        card: Card,
        stack_depth: int,
        boat_params: BoatParams,
        with_cutouts: bool,
) -> SVGGroup:
    full_card_width = card.width + boat_params.tolerance
    full_stack_depth = stack_depth + boat_params.tolerance
    front_size = boat_params.front_size(card.height)
    side_size = boat_params.side_size(card.height)
    front_radius = front_size - side_size

    group = drawing.g()

    # Drawing outline of the whole box.
    #
    #        0+---------+17
    #         |Title    |
    #        1+---------+16
    #         |  Back   |
    #        2|         |15
    #     3+--+---------+--+14
    #  5  4|  | Bottom  |  |13  <– bottom flaps
    #   +--+--+---------+--+--+12
    #   |  |  |  Front  |  |  |  <– side flaps
    #  6+--+--|         |--+--+11
    #      7 8+---------+9 10
    path_drawer = PathDrawer()

    path_drawer.move(boat_params.flap_length + full_stack_depth + boat_params.rounding_radius, 0)
    # 0
    path_drawer.draw_arc(-boat_params.rounding_radius, boat_params.rounding_radius, boat_params.rounding_radius)
    # 2
    path_drawer.draw_down(boat_params.boat_height - boat_params.rounding_radius)

    if with_cutouts:
        path_drawer.draw_down(full_stack_depth)
        path_drawer.draw_up(full_stack_depth)
    if with_cutouts:
        path_drawer.draw_right(full_card_width)
        path_drawer.draw_left(full_card_width)

    # 3
    path_drawer.line_by(-boat_params.flap_length, boat_params.flap_cut)
    # 4
    path_drawer.draw_down(full_stack_depth - boat_params.flap_cut * 2)
    path_drawer.line_by(boat_params.flap_length, boat_params.flap_cut)
    # 5
    if with_cutouts:
        path_drawer.draw_down(side_size)
        path_drawer.draw_up(side_size)
        path_drawer.draw_right(full_card_width)
        path_drawer.draw_left(full_card_width)

    path_drawer.draw_left(full_stack_depth)
    if with_cutouts:
        path_drawer.draw_down(side_size)
        path_drawer.draw_up(side_size)

    path_drawer.line_by(-boat_params.flap_length, boat_params.flap_cut)
    # 6
    path_drawer.draw_down(side_size - boat_params.flap_cut * 2)
    # 7
    path_drawer.line_by(boat_params.flap_length, boat_params.flap_cut)
    path_drawer.draw_right(full_stack_depth)
    # 8
    path_drawer.draw_arc(front_radius, front_radius, front_radius)
    # 9
    path_drawer.draw_right(full_card_width - 2 * front_radius)
    # 10
    path_drawer.draw_arc(front_radius, -front_radius, front_radius)
    # 11
    path_drawer.draw_right(full_stack_depth)
    path_drawer.line_by(boat_params.flap_length, -boat_params.flap_cut)
    # 12
    path_drawer.draw_up(side_size - 2 * boat_params.flap_cut)
    # 13
    path_drawer.line_by(-boat_params.flap_length, -boat_params.flap_cut)

    if with_cutouts:
        path_drawer.draw_down(side_size)
        path_drawer.draw_up(side_size)

    path_drawer.draw_left(full_stack_depth)

    if with_cutouts:
        path_drawer.draw_down(side_size)
        path_drawer.draw_up(side_size)

    path_drawer.line_by(boat_params.flap_length, -boat_params.flap_cut)
    # 14
    path_drawer.draw_up(full_stack_depth - 2 * boat_params.flap_cut)
    path_drawer.line_by(-boat_params.flap_length, -boat_params.flap_cut)

    if with_cutouts:
        path_drawer.draw_down(full_stack_depth)
        path_drawer.draw_up(full_stack_depth)
    # 15
    path_drawer.draw_up(boat_params.boat_height - boat_params.rounding_radius)
    # 17
    path_drawer.draw_arc(-boat_params.rounding_radius, -boat_params.rounding_radius, boat_params.rounding_radius)
    path_drawer.close()

    path = drawing.path(d=path_drawer.get_draw_command(), fill="none", stroke="black", stroke_width=HAIRLINE_THIN)
    group.add(path)

    size_diff = boat_params.boat_height - card.height
    offset = 2
    box_size = size_diff - offset * 2
    bottom_image_size = int(front_size * 0.8)

    image_data = get_image_data(pathlib.Path('icons/monsters/vyraxen.svg'))
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

    # group.add(
    #     drawing.text(
    #         "01234567890",
    #         insert=(
    #             boat_params.flap_length + full_stack_depth + 2 * boat_params.rounding_radius + offset + box_size,
    #             offset + box_size,
    #         ),
    #         font_size=f'{box_size}pt',
    #         font_family="Katari",
    #         fill="black",
    #         text_anchor="start",
    #     )
    # )

    return group


def save_boat(filename: str, **kwargs) -> None:
    drawing = svgwrite.Drawing(
        filename=filename,
        size=SIZE,
        viewBox=VIEW_BOX,
        profile='tiny',
    )

    group = draw_boat(
        drawing=drawing,
        card=Card(88, 63),
        stack_depth=10,
        boat_params=BoatParams(),
        **kwargs,
    )
    group.translate(20, 20)
    drawing.add(group)

    buffer = io.StringIO()
    drawing.write(buffer)
    cairosvg.svg2svg(buffer.getvalue(), write_to=filename)


def main() -> None:
    save_boat('internal.svg', with_cutouts=True)
    save_boat('external.svg', with_cutouts=False)


if __name__ == '__main__':
    main()
