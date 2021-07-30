FROM 10.10.104.21:5000/python:3.6-alpine


RUN /usr/local/bin/python -m pip install --upgrade pip
RUN pip3 install --no-cache-dir pywemo paho-mqtt pyyaml schedule


COPY ./wemo_mqtt.py /bin/wemo_mqtt.py
RUN chmod 755 /bin/wemo_mqtt.py

COPY ./wemo.yaml /wemo.yaml

CMD ["/usr/local/bin/python3","-u","/bin/wemo_mqtt.py"]
