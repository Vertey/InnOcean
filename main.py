# InnOcean Salinity-pH Control Loop
# Takes in values for temperature, pH and salinity
# Uses effectors like salt dispenser, alkali dispenser and fresh water pump
# Constantly adjusts values in a close loop according to predefined conditions

import sys
sys.path.append('../')
import time
import math
from DFRobot_ADS1115 import ADS1115
from DFRobot_PH import DFRobot_PH
from DFRobot_EC import DFRobot_EC

#Sensors
ads1115 = ADS1115()
df_ec      = DFRobot_EC()
df_ph      = DFRobot_PH()
temperature = 25
ads1115.setAddr_ADS1115(0x48)
adc0 = ads1115.readVoltage(0)
adc1 = ads1115.readVoltage(1)

df_ec.begin()
df_ph.begin()

#Relays
Relay_Ch1 = 26
Relay_Ch2 = 20 
Relay_Ch3 = 21

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

GPIO.setup(Relay_Ch1,GPIO.OUT)
GPIO.output(Relay_Ch1, GPIO.HIGH)

GPIO.setup(Relay_Ch2,GPIO.OUT)
GPIO.output(Relay_Ch2, GPIO.HIGH)

GPIO.setup(Relay_Ch3,GPIO.OUT)
GPIO.output(Relay_Ch3, GPIO.HIGH)

#Servo
ph_servoPIN = 4
sal_servoPIN = 22


def measure_salinity():
    #DEFINE SALINITY MEASUREMENT
    #return float(input('sal>' ))
    ec = df_ec.readEC(adc0['r'],temperature)
    tds = 0.89 * ec * 0.1
    sal = tds / 100.
    print "Salinity: " + str(sal)
    return sal 
    
def run_salt_disp(grams):
    #DEFINE RUNNING THE SALT DISPENSER
    revol = grams / 3
    GPIO.setup(sal_servoPIN, GPIO.OUT)
    p = GPIO.PWM(sal_servoPIN, 50)
    
    GPIO.output(Relay_Ch2,GPIO.LOW)
    p.ChangeDutyCycle(8.75)
    p.start(1)
    time.sleep(revol * 1.4)   	
    GPIO.output(Relay_Ch2, GPIO.HIGH)
    print 'Salt dispenser dispensed grams of NaCl: ' + str(grams)


def run_ph_disp(grams):
    #DEFINE RUNNING pH DISPENSER
    revol = grams / 3
    GPIO.setup(ph_servoPIN, GPIO.OUT)
    p = GPIO.PWM(ph_servoPIN, 50)
    
    GPIO.output(Relay_Ch1,GPIO.LOW)
    p.ChangeDutyCycle(8.75)
    p.start(1)
    time.sleep(revol * 1.4)   	
    GPIO.output(Relay_Ch1, GPIO.HIGH)
    print 'pH dispenser dispensed grams of Na2CO3: ' + str(grams)


def run_pumps(liters):
    #DEFINE PUMP RUNTIME
    rate = 0.02778
    runtime = float(liters) / rate
    
    GPIO.output(Relay_Ch3,GPIO.LOW)
    time.sleep(runtime)
    GPIO.output(Relay_Ch3,GPIO.HIGH)
    print 'Pumps displaced liters of water: ' + str(liters)


def simulate_sal(volume, sal , water_displaced, salt_added):

    salt_lost = water_displaced * sal * 1000
    new_sal_grams = volume * sal * 1000 - salt_lost + salt_added
    new_sal = (new_sal_grams / 1000) / volume
    
    return new_sal


def simulate_ph(volume, pH, water_displaced, alkali_added):

    mr_Na2CO3 = 105.99
    pKa = 10.33
    Kw = 1.008E-14
    Ka = math.pow(10, -pKa)
    Kb = Kw / Ka
    pKw = -math.log10(Kw)

    pOH = pKw - pH
    conc_OH = math.pow(10, -pOH)
    conc_alkali = math.pow(conc_OH, 2) / Kb + conc_OH
    grams_alkali = conc_alkali * (volume - water_displaced) * mr_Na2CO3

    new_grams_alkali = grams_alkali + alkali_added
    new_conc_alkali = (float(new_grams_alkali) / mr_Na2CO3) / float(volume)
    discriminant = math.pow(Kb, 2) + 4 * Kb * new_conc_alkali
    new_conc_OH = (math.sqrt(discriminant) - Kb) / 2
    new_pOH = -math.log10(new_conc_OH)
    new_pH = pKw - new_pOH

    return new_pH
    
    
def ph_to_grams(pH, volume):
	
    mr_Na2CO3 = 105.99
    pKa = 10.33
    Kw = 1.008E-14
    Ka = math.pow(10, -pKa)
    Kb = Kw / Ka
    pKw = -math.log10(Kw)
    
    pOH = pKw - pH
    conc_OH = math.pow(10, -pOH)
    conc_alkali = math.pow(conc_OH, 2) / Kb + conc_OH
    grams_alkali = conc_alkali * volume * mr_Na2CO3
    
    return grams_alkali


def input_conditions():
    #OBTAIN THESE FROM A DIFFERENT PART OF CODE THAT TAKES CARE OF USER INTERACTIONS
    conditions = {
        'species': 'Seaweed Species',
        'volume': 20,
        'target_sal': [0.028, 0.032],
        'target_pH': [8.4, 8.8],
    }
    return conditions


def main():
    n_cycles = int(input('Input number of cycles to perform: '))
    wait_time = int(input('Input time in seconds between cycles: '))

    # Reads and prepares input conditions
    conditions = input_conditions()
    volume = conditions['volume']
    min_sal = conditions['target_sal'][0]
    max_sal = conditions['target_sal'][1]
    min_ph = conditions['target_pH'][0]
    max_ph = conditions['target_pH'][1]
    mr_Na2CO3 = 105.99
    water_displaced = 0.
    alkali_added = 0.
    salt_added = 0.

    # Converts concentration and pH to grams
    min_sal_grams = min_sal * volume * 1000
    max_sal_grams = max_sal * volume * 1000
    min_ph_grams = ph_to_grams(min_ph, volume)
    max_ph_grams = ph_to_grams(max_ph, volume)

    i = 1
    while i <= n_cycles:
        print 'Cycle nr ' + str(i)
        sal = measure_salinity()
        ph = df_ph.readPH(adc1['r'],temperature)
        print ph 
        sal_grams = sal * volume * 1000
        ph_grams = ph_to_grams(ph, volume)

        # Checks for too much salt or alkali
        if sal_grams > max_sal_grams or ph_grams > max_ph_grams:
            if ph_grams > max_ph_grams:
                run_pumps(1)
                water_displaced = 1
            else:
                run_pumps(0.5)
                water_displaced = 0.5
        else:
            run_pumps(0)

        # Checks for too little alkali
        if ph_grams < min_ph_grams:
            run_ph_disp(0.5)
            alkali_added = 0.5
        else:
            run_ph_disp(0)

        # Checks for too little salt
        if sal_grams < min_sal_grams:
            run_salt_disp(20)
            salt_added = 20
        else:
            run_salt_disp(0)

        new_sal = simulate_sal(volume, sal, water_displaced, salt_added)
        print 'Predicted salinity in % is: ' + str(100 * new_sal)
        new_ph = simulate_ph(volume, ph, water_displaced, alkali_added)
        print 'Predicted pH is: ' + str(new_ph)

        print 'Waiting for time in seconds:' + str(wait_time)
        print ''
        i += 1
        time.sleep(wait_time)

    GPIO.cleanup()	
    print 'Control loop closed'


main()
