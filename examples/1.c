#include <stdio.h>

struct struct_a {
    int a;
};
struct struct_a obj_a = {
    .a = 1,
};

struct struct_b {
    int b;
} obj_b = {
    .b = 114514,
};

struct {
    int c;
} obj_c = {
    .c = 12,
};

struct st_members {
    int a;
    int b;
    int c;
};

struct st_members_2 {
    int a;
    int b, c;
    int d;
};

int main()
{
    return 0;
}
