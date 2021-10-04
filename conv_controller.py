#!/usr/bin/env python3

from conversator import puszczenie_pierwszej_wiadomosci_i_zapis_do_databazy_tnd, \
klikanie_tnd, odpowiedz_tnd, uruchomienie_tnd, zamkniecie_tnd, \
usuwanie_przeterminowanych_dziewczyn, obliczanie_ilosci_dziewczyn_do_pisania, \
PowiadomieniaPushbullet
from random import randint
from datetime import datetime, timedelta, time
from time import sleep
from traceback import print_exc


class KierownikSesji:
    def __init__(self):
        self.poczatek_1_sesji = 0
        self.poczatek_2_sesji = 0

    def sesja_1(self):
        try:
            uruchomienie_tnd()
            klikanie_tnd(randint(2, 6))
            puszczenie_pierwszej_wiadomosci_i_zapis_do_databazy_tnd(randint(2, 4))
            odpowiedz_tnd()
            zamkniecie_tnd()
        except:
            powiadom.wyslij_powiadomienie_o_wywaleniu_sie_apki()
            print_exc()

    def sesja_2(self):
        try:
            uruchomienie_tnd()
            # sprawdzanie etapu dziewczyny
            if odpowiedz_tnd() == True:
                # powtarzamy odpowiedź w przypadku wysłanego zaproszenia,
                # by odczytać jeszcze tego dnia
                sleep(randint(5200, 5600))
                odpowiedz_tnd()
            usuwanie_przeterminowanych_dziewczyn()
            zamkniecie_tnd()
        except:
            powiadom.wyslij_powiadomienie_o_wywaleniu_sie_apki()
            print_exc()


sesje = KierownikSesji()
powiadom = PowiadomieniaPushbullet()

# pętla nieskoncona
while True:
    # losowanie czasów sesji
    if datetime.now().time() > time(17, 50) and datetime.now().time() < time(18, 0):
        sesje.poczatek_1_sesji = randint(0, 49)
        sesje.poczatek_2_sesji = randint(0, 49)
        print(f'Dziś sesje rozpoczną się się w ciągu 10 min po godzinach 18:{sesje.poczatek_1_sesji} i 21:{sesje.poczatek_2_sesji}')
    # wybór czasu pierwszej sesji i uruchomienie
    if datetime.now().time() > time(18, sesje.poczatek_1_sesji) and \
        datetime.now().time() < time(18, 10+sesje.poczatek_1_sesji):
        # dać tryexcepta przy sesjach
        sesje.sesja_1()
    # wybór czasu drugiej sesji i uruchomienie
    elif datetime.now().time() > time(21, sesje.poczatek_1_sesji) and \
        datetime.now().time() < time(21, 10 + sesje.poczatek_1_sesji):
        sesje.sesja_2()
    # spanie około 10 min, nie dokładnie by uniknąć powtarzania się pory
    sleep(589)
