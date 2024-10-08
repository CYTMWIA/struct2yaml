struct struct_d {
    int d;
    struct struct_b sb;
} obj_d = {
    .d = 12,
    .sb.b = 34,
};

enum enum_a {
    ENUM_A_1 = 0,
    ENUM_A_2,
};

struct struct_e {
    enum enum_a ea;
};
