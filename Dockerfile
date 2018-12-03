FROM veyalla/vector:0.4

COPY vector_vision_sdk.py /
COPY start.sh /
RUN sed -i 's/\r//' ./start.sh && \
    chmod u+x start.sh

ENTRYPOINT ["./start.sh"]
