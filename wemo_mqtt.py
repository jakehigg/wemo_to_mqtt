#!/usr/bin/python3

#Install dependancy:
#sudo pip3 install pywemo
#sudo pip3 install paho-mqtt
#sudo pip3 install schedule
#sudo pip3 install astral
import sys
import pywemo
import paho.mqtt.client as mqtt
import time
import datetime
import yaml as yaml
#from multiprocessing import Process
import threading

try:
    import thread
except ImportError:
    import _thread as thread

class WemoMQTT():
    """manage wemo devices from mqtt"""

    def __init__(self, yaml_file, mqtt_broker_ip):
        """initialize class and setup"""

        #set vars
        self.debug = True
        self.poll_interval = 30 #seconds
        self.refresh_interval = 120 #seconds
        self.mqtt_broker_addr = mqtt_broker_ip
        self.topic_base = "wemo/"
        self.topic_cmd = "/control"
        self.topic_status = "/status"
        self.disconnected_wemo_registry = []
        self.wemo_registry = []

        self.connect_mqtt_broker()



        print("Loading yaml")
        with open(yaml_file, 'r') as stream:
            try:
                yaml_content = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)


        for wemo_ip in yaml_content["static"]:
            print("connecting to", wemo_ip)
            self.register_wemo(wemo_ip)


        
    def connect_mqtt_broker(self):
        """Connect to mqtt broker and start mqtt loop"""
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.connect(self.mqtt_broker_addr,1883,60)
        #self.mqtt_client.on_message = on_message
        #Start the MQTT thread that handles this client
        self.mqtt_client.loop_start()


    def register_wemo(self, wemo_ip):
        """used to register an individual wemo and publish it's state"""
        url = pywemo.setup_url_for_address(wemo_ip)
        if url is None:
            print("error connecting to:", wemo_ip)
            if wemo_ip in self.disconnected_wemo_registry:
                #cant reconnect to disconnected
                if self.debug:
                    print("cant reconnect to ", wemo_ip)
            else:
                self.disconnected_wemo_registry.append(wemo_ip)
        else:
            wemo = pywemo.discovery.device_from_description(url)
            if wemo:
                self.wemo_registry.append(wemo)
                if self.debug:
                    print(wemo.name.lower().replace(" ", "_"))
                if wemo.host in self.disconnected_wemo_registry:
                    self.disconnected_wemo_registry.remove(wemo.host)
            else: 
                self.disconnected_wemo_registry.append(wemo_ip)
        
        return self.poll_wemo(wemo)


    def refresh_disconnected_wemos(self):
        """call regularly to go through the disconnected registry and attempt to register"""
        for disconnected_wemo in self.disconnected_wemo_registry:
            self.register_wemo(disconnected_wemo)



    def poll_wemo(self, wemo):
        """poll a wemo and test connectivity and publish state"""

        def quit_function(fn_name):
            # print to stderr, unbuffered in Python 2.
            print('{0} took too long'.format(fn_name), file=sys.stderr)
            sys.stderr.flush() # Python 3 stderr is likely buffered.
            thread.interrupt_main() # raises KeyboardInterrupt

        def exit_after(s):
            '''
            use as decorator to exit process if 
            function takes longer than s seconds
            '''
            def outer(fn):
                def inner(*args, **kwargs):
                    timer = threading.Timer(s, quit_function, args=[fn.__name__])
                    timer.start()
                    try:
                        result = fn(*args, **kwargs)
                    finally:
                        timer.cancel()
                    return result
                return inner
            return outer

        @exit_after(10)
        def test_connectivity(wemo):
            t = "String"
            t = wemo.get_state(force_update=True)
            if t != "String":
                return True
            else:
                return False

        @exit_after(15)
        def try_reconnect_wemo(wemo):
            ip = wemo.host
            if self.debug:
                print("trying to reconnect to", ip)
            url = pywemo.setup_url_for_address(ip)
            if self.debug:
                print("url is", url)
            new_wemo = None
            new_wemo = pywemo.discovery.device_from_description(url)    
            if new_wemo:
                return True
            else:
                return False



        availability = "online"
        if test_connectivity(wemo):
            new_state = wemo.get_state(force_update=True)
            state = "on"
            if new_state == 0:
                state = "off"
        elif try_reconnect_wemo(wemo):
            new_state = wemo.get_state(force_update=True)
            state = "on"
            if new_state == 0:
                state = "off"
        else:
            availability = "offline"
            state = "off"
            self.wemo_registry.remove(wemo)
            self.disconnected_wemo_registry.add(wemo.host)

        self.publish_status(wemo, availability, state)

        if availability == "online":
            return True
        else:
            return False

    def publish_status(self, wemo, availability, state):
        """publishes a status of a connected wemo"""
        base_topic = self.topic_base + wemo.name.lower().replace(" ", "_")
        status_topic = self.topic_base + wemo.name.lower().replace(" ", "_") + self.topic_status
        wemo_ip = wemo.host

        if self.debug:
            print("Publishing State for ", wemo.name)
            print("device is ", state)


        self.mqtt_client.publish(status_topic, retain=True, payload=state)
        self.mqtt_client.publish(base_topic + "/type", retain=True, payload="%s" % wemo.device_type.lower().replace(" ", "_"))
        self.mqtt_client.publish(base_topic + "/ip", retain=True, payload=wemo_ip)
        self.mqtt_client.publish(base_topic + "/availability", retain=True, payload=availability)
        
    def refresh_wemos(self):
        for wemo in self.wemo_registry:
            self.poll_wemo(wemo)


