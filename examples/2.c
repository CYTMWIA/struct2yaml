struct StructWithInit {
    int a;
    float b;
    char c;
} struct_with_init = {
    .a = 1,
};

struct NestedStructWithInit {
    int a;
    float b;
    char c;
    struct {
        int inner;
    } d;
} nested_struct_with_init = {
    .a = 1,
    .d.innner = 1
};

enum enum_example {
    ENUM_1 = 0,
    ENUM_2,
};
typedef enum enum_example enum_example_e;

struct StructEnum {
    enum enum_example e1;
    enum_example_e e2;
};

struct EveryingStruct {
    int a;
    int b, c, d;
    int *e;
    const int f;
    int g[20]; 
    enum enum_example e1;
    enum_example_e e2;
    struct StructEnum n1;
    struct {
        int na;
        struct {
            int nna;
        } nn1;
    } n2;
} everying_struct = {

};
