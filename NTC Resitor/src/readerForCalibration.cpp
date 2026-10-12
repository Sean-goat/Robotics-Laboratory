#include <math.h> // Til log() og pow()
#include <Arduino.h>
// --- Konstanter fra Del 2 ---
const int ADC_PIN = 4;
const double V_IN = 3.3;
const double R_FAST = 10000.0;
const double ADC_MAX = 4095.0;
// --- JERES KALIBREREDE PARAMETRE HER ---
// (EKSEMPEL-værdier. SKAL UDSKIFTES!)
const double SH_A = 2.3037727499e-03;
const double SH_B = -1.6421660544e-05;
const double SH_C = 1.7160699282e-06;

void setup() {
    Serial.begin(115200);
    Serial.println("NTC Termometer (5 Hz)");
    analogReadResolution(12);
}

void loop() {
    // 1-3. Beregn R_NTC (som i Del 2)
    int adc_raw = analogRead(ADC_PIN);
    double v_out = (adc_raw / ADC_MAX) * V_IN;  
    double r_ntc = R_FAST * (v_out / (V_IN - v_out));

    // 4. Beregn Temperatur med Steinhart-Hart
    double lnR = log(r_ntc);

    // 1/T = A + B*ln(R) + C*(ln(R))^3
    double T_kelvin = 1.0 / (SH_A + (SH_B * lnR) + (SH_C * pow(lnR, 3)));
    // 5. Konvertér til Celsius
    double T_celsius = T_kelvin - 273.15;

    // 6. Udskriv resultatet (5 gange/sek)
    Serial.print("R: ");
    Serial.print(r_ntc, 0);
    Serial.print(" Ohm\t");
    Serial.print("Temp: ");
    Serial.print(T_celsius, 2);
    Serial.println(" °C");
}
