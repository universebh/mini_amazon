#!/bin/bash

rm -rf *.pyc world_amazon_pb2.py
protoc -I=. --python_out=. ./world_amazon.proto