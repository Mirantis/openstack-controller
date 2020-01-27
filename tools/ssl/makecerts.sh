#!/usr/bin/env bash
mkdir -p certs
pushd certs
if [ ! -f 'cfssl' ]; then
    curl -L https://pkg.cfssl.org/R1.2/cfssl_linux-amd64 -o cfssl
fi
if [ ! -f 'cfssljson' ]; then
    curl -L https://pkg.cfssl.org/R1.2/cfssljson_linux-amd64 -o cfssljson
fi
chmod +x cfssl
chmod +x cfssljson
./cfssl gencert -initca ../ca-csr.json | ./cfssljson -bare ca
./cfssl gencert -ca=ca.pem -ca-key=ca-key.pem --config=../ca-config.json -profile=kubernetes ../server-csr.json | ./cfssljson -bare server
popd
