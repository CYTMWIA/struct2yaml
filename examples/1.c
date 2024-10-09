#include <stdio.h>

struct SingleMember {
    int value;
};

struct MultiMember {
    int a;
    float b;
    char c, d;
};

struct {
    int x;
    float y;
} anonymous_struct;

struct NestedStruct {
    int outer;
    struct SingleMember nested;
};

struct NestedAnonymousStruct {
    int outer;
    struct {
        int inner;
    } nested;
};

typedef struct {
    int id;
    char name[20];
} TypedefStruct;

struct IncompleteInitialization {
    int p;
    float q;
    char r;
} incompleteInit = {10};

struct Outer {
    int outerValue;
    struct {
        int innerValue;
    } anonymousInner;
};

int main()
{
    return 0;
}
