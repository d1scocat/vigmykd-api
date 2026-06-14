# vigmykd-api
very intense game makes your keyboard die, but it's the REST API

## on AI
not a single line of code was written by ai here. i take pride in my ability to cook up REST APIs and i will subsequently take great offence if i am even suggested to use ai to write code for me.

the only purpose that ai served was consulting me several times on sparsely documented APIs like motor (for which i had to look into pymongo docs instead) and some design choices for fastapi (mostly package structuring, etc). i went to great lengths to ensure that not a single line of code from ai got into here.

## JWT keys
generate the keys using any method you feel like is your favorite, e.g.:
```bash
# generate a 2048-bit RSA private key
openssl genpkey -algorithm RSA -out private_key.pem -pkeyopt rsa_keygen_bits:2048

# extract the corresponding public key
openssl rsa -pubout -in private_key.pem -out public_key.pem
```

# proto compilation
compile .proto files like this (example):
```bash
pwd
> ~/vigmykd-api
protoc --python_out=.\src\vigmykd\generated\. .\proto\v1\packet.proto
```