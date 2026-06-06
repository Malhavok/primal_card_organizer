// To be used with OpenScad.
width = 392;
depth = 430;
height = 80;

wall = 2;
tol = 1;


module boxes() {
// Weapon stacks.
weapon_depth = 125;
weapon_stack_1_width = 102;
translate([0, depth - weapon_depth])
cube([weapon_stack_1_width, weapon_depth, height]);

weapon_stack_2_width = 70;
translate([0, depth - weapon_depth * 2 - wall, 0])
cube([weapon_stack_2_width, weapon_depth, height]);

// Characters.
characters_width = width - weapon_stack_1_width - wall;
character_depth = 93;

translate([width - characters_width, depth - character_depth, 0])
cube([characters_width, character_depth, height]);

// Monsters.
monster_width = character_depth;
monster_12_depth = 323;
monster_3_depth = 125;
character_to_monster_depth = depth - character_depth - monster_12_depth;
monster_3_translate_depth = depth - character_depth - character_to_monster_depth - monster_3_depth;

translate([width - monster_width, 0, 0])
cube([monster_width, monster_12_depth, height]);

translate([width - monster_width * 2 - wall, 0, 0])
cube([monster_width, monster_12_depth, height]);

translate([width - monster_width * 3 - wall * 2, monster_3_translate_depth, 0])
cube([monster_width, monster_3_depth, height]);

// Havok deck.
havok_depth = 7;

translate([width - monster_width * 3 - wall * 2, monster_3_translate_depth - wall - havok_depth, 0])
cube([monster_width, havok_depth, height]);

// Attrition decks.
attrition_depth = 48;
blood_width = attrition_depth;
blood_depth = 10;
quest_width = 32;
attrition_width = 22;

translate([width - monster_width * 3 - wall * 2 + (monster_width - blood_width) / 2, monster_3_translate_depth - wall * 2 - havok_depth - blood_depth, 0])
cube([blood_width, blood_depth, height]);

translate([width - monster_width * 3 - wall * 3 - quest_width, depth - weapon_depth - wall - attrition_depth, 0])
cube([quest_width, attrition_depth, height]);

translate([width - monster_width * 3 - wall * 3 - attrition_width, depth - weapon_depth - wall * 2 - attrition_depth * 2, 0])
cube([attrition_width, attrition_depth, height]);

// Equipments.
equipment_width = 66;
equipment_1_depth = 105;
equipment_23_depth = 170;
equipment_special_depth = 60;

cube([equipment_width, equipment_1_depth, height]);

translate([0, equipment_1_depth + wall, 0])
cube([equipment_width, equipment_special_depth, height]);

translate([equipment_width + wall, 0, 0])
cube([equipment_width, equipment_23_depth, height]);

translate([(equipment_width + wall) * 2, 0, 0])
cube([equipment_width, equipment_23_depth, height]);
}

module insert() {
difference() {
translate([0.5, 0.5, 0])
cube([width - 1, depth - 1, height / 2]);

translate([0, 0, 2])
boxes();
}
}

module quarter() {
translate([0, 0, -1])
cube([width / 2, depth / 2, height + 2]);
}

intersection() {
insert();

// translate([0, 0, 0])
// quarter();

// translate([0, depth / 2, 0])
// quarter();

// translate([width / 2, 0, 0])
// quarter();

translate([width / 2, depth / 2, 0])
quarter();
}
