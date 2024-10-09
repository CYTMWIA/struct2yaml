#!/bin/bash

examples="examples/1.c examples/2.c"

uv run struct2yaml.py -i $examples --output_type ast > ast.txt

uv run struct2yaml.py -i $examples --output_type yaml --identifier struct_b
