import schedule
import wemo_mqtt 
import time 

wemo_class = wemo_mqtt.WemoMQTT("./wemo.yaml", "")


schedule.every(wemo_class.poll_interval).seconds.do(wemo_class.refresh_wemos)
schedule.every(wemo_class.refresh_interval).seconds.do(wemo_class.refresh_disconnected_wemos)



while(True):
    schedule.run_pending()
    if wemo_class.debug:
        print("looping")
    time.sleep(10)


