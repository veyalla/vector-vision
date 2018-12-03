#!/bin/bash

rm -f ~/.anki_vector/sdk_config.ini || true 
echo '=> creating sdk_config.ini'
cat <<EOF > ~/.anki_vector/sdk_config.ini
[007019ca]
cert = /root/.anki_vector/Vector-Y3D6-007019ca.cert
ip = $VECTORIP
name = Vector-Y3D6
guid = edAOw0e5RT6Ksy3Jg2EXRg==
EOF

echo '=> running vector vision sdk program'
exec python -u /vector_vision_sdk.py
