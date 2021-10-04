from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait as Wait
from selenium.webdriver.support import expected_conditions as ExpCon
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, \
    NoSuchElementException, ElementNotInteractableException
import time
from datetime import datetime, timedelta
import random
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker
from wit import Wit
import re
from emoji import demojize
import smtplib
import ssl
from sys import platform
from tenacity import retry, stop_after_attempt
from pushbullet import Pushbullet

# zmienna globalna drivera przeglądarki
driver = None

# klient Wit.ai
client_wit = Wit('')    # wstaw tu nr klirnta wit

# inicjalizacja databazy
engine = create_engine('sqlite:///Conversator.db?check_same_thread=False')
BazaCzyliKlasaRodzicznaDatabazy = declarative_base()


class TabelaTekstow(BazaCzyliKlasaRodzicznaDatabazy):
    __tablename__ = 'Teksty'
    id = Column(Integer, primary_key=True)
    etap = Column(Integer)
    tag = Column(String)
    tekst = Column(String)

    def __repr__(self):
        return self.tekst


class TabelaDziewczyn(BazaCzyliKlasaRodzicznaDatabazy):
    __tablename__ = 'Spis dziewczyn'
    id = Column(Integer, primary_key=True)
    imiewiek = Column(String)
    etap = Column(Integer)
    tagi = Column(String)
    uwagi = Column(String)
    portal = Column(String)
    #poczatek = Column(DateTime, default=datetime.today())
    czas_ostaniej_aktywnosci = Column(DateTime, default=datetime.today())

    def __repr__(self):
        return self.imie


class TabelaSmietnikowa(BazaCzyliKlasaRodzicznaDatabazy):
    __tablename__ = 'Smietnik'
    id = Column(Integer, primary_key=True)
    imiewiek = Column(Integer)
    etap = Column(Integer)
    tagi = Column(String)
    portal = Column(String)
    poczatek = Column(DateTime, default=datetime.today())
    czas_ostaniej_aktywnosci = Column(DateTime, default=datetime.today())

    def __repr__(self):
        return self.imie

BazaCzyliKlasaRodzicznaDatabazy.metadata.create_all(engine)
Sesion = sessionmaker(bind=engine)  #, autocommit=True)
sesja = Sesion()


class PowiadomieniaPushbullet():
    def __init__(self):
        PUSHBULLET_TOKEN = ''   # insert token here
        self.pushbullet = Pushbullet(PUSHBULLET_TOKEN)

    def wyslij_powiadomienie_o_dziewczynie(self, imiewiek):
        imie = imiewiek[:-3]
        wiek = imiewiek[-3:]
        tytul = 'Zapowiada się randka!'
        tresc = f'Chce się z Tobą spotkać {imie}, lat {wiek}. Zaprosiłem na jutro.'
        self.pushbullet.push_note(tytul, tresc)

    def wyslij_powiadomienie_o_wywaleniu_sie_apki(self):
        tytul = 'Ratunku!'
        tresc = f'Apka się wywaliła. Potrzebna pomoc.'
        self.pushbullet.push_note(tytul, tresc)

powiadom = PowiadomieniaPushbullet()

# funkcje
def uruchomienie_tnd():
    global driver
    # stworzenie drivera przeglądarki dla selenium
    profilFF = webdriver.FirefoxProfile('FirefoxProfile')
    driver = webdriver.Firefox(profilFF)
    karta_laski_xpath = "//div[1]/div[1]/div[1]/div[1]/div[3]/div[1]/div[1]/span[1]/div[1]"
    ladowanie_strony_glownej(karta_laski_xpath)
    # powiększam okno, by uniknąć StaleErrora (nie mieszczące się napisy)
    driver.maximize_window()
    print('czekam profilaktycznie')
    # udawanie człowieka
    time.sleep(random.uniform(1, 4))


def zamkniecie_tnd():
    print('zamykam tindera')
    # czeka chwilę przed zamykaniem
    time.sleep(random.uniform(3, 6))
    driver.close()

@retry(stop=stop_after_attempt(3))
def ladowanie_strony_glownej(karta_laski_xpath):
    driver.get("https://tinder.com")
    print('czekam, aż załaduje się strona')
    # czeka, aż karta laski się załąduje
    Wait(driver, random.uniform(85, 100)).until(
            ExpCon.presence_of_element_located((By.XPATH, karta_laski_xpath)))


def puszczenie_pierwszej_wiadomosci_i_zapis_do_databazy_tnd(ilosc_do_napisania=5):
    # zmienne
    imiewiek_xpath = "//div[@class='My(2px) C($c-base) Us(t) D(f) Ai(b) Maw(90%)']"
    nr_dziewczyny_od_konca = 1
    # udawanie człowieka
    time.sleep(random.uniform(0.3, 0.6))

    i = 0
    while i < ilosc_do_napisania:
        # kliknięcie w pary (niepisane)
        driver.find_element_by_xpath(match_tab_xpath()).click()
        #Wait(driver, 30).until(ExpCon.presence_of_element_located((ikonka)))
        time.sleep(random.uniform(1, 2))
        ikonki = driver.find_elements_by_xpath(ikonki_xpath())
        if len(ikonki) == 1:
            print('nie ma dziewczyn do pisania')
            return
        # klikamy w najstarszą dziewczynę
        ikonki[-nr_dziewczyny_od_konca].click()
        # czekanie, by poprzednia dziewczyna zdążyłą znikąć i wait ją nie
        # pomylił z nową
        time.sleep(0.25)
        Wait(driver, 30).until(ExpCon.presence_of_element_located((By.XPATH,
            imiewiek_xpath)))
        imiewiek = driver.find_element_by_xpath(imiewiek_xpath).text
        imie = imiewiek[:-3]
        #zapisujemy dziewczynę do databazy, chyba że już jest taka sama
        if dodanie_do_databazy(imiewiek) == 'jest_juz':
            nr_dziewczyny_od_konca +=1
            continue
        # wybieramy wiadomości
        wiadomosci = wybor_pierwszej_wiadomosci(imie)
        # przeglądanie profilu i zastanawianie sie nad pierwszą wiadomością
        print('przeglądam profil i dumam nad pierwszą wiadomością')
        time.sleep(random.uniform(15, 22))
        wysylanie_wiadomosci_tnd(wiadomosci)
        i += 1


def wybor_pierwszej_wiadomosci(imie):
    wolacz = imie_to_imie_w_wolaczu(imie)
    # pobieranie tekstu z databazy
    tekst = sesja.query(TabelaTekstow).filter(TabelaTekstow.etap == 1).all()[0]
    # poniższy wiersz po to, by z tekstem robić operacje jak z innymi stringami
    tekst = str(tekst)
    tekst = tekst.format(wolacz)
    wiadomosci = tekst.split('\r\n')
    return wiadomosci


def dodanie_do_databazy(imiewiek):
    czas = datetime.now()
    portal = 'tnd'
    # szuka, czy nie ma już w bazie danych dziewczyny
    # o tym samym imieniu i wieku
    if len(sesja.query(TabelaDziewczyn).filter(
            TabelaDziewczyn.imiewiek == imiewiek).all()) != 0:
        return 'jest_juz'
    # zapis dziewczyny do databazy
    nowa_dziewczyna = TabelaDziewczyn(imiewiek=imiewiek, etap=1,
        portal=portal, czas_ostaniej_aktywnosci=czas)
    sesja.add(nowa_dziewczyna)
    sesja.commit()


def wysylanie_wiadomosci_tnd(wiadomosci):
    text_area_xpath = "//div[1]/div[1]/div[1]/div[1]/div[1]/div[3]/form[1]/textarea[1]"
    # wpisanie wiadomości
    pole_tekstowe = driver.find_element_by_xpath(text_area_xpath)
    for wiadomosc_dtb in wiadomosci:
        wiadomosc = str(wiadomosc_dtb)
        # zastanawianie się, co napisać
        print('dumam, co by tu napisać...')
        time.sleep(random.uniform(5, 10))
        pole_tekstowe.send_keys(wiadomosc)
        # udawanie człowieka
        print('piszę...')
        time.sleep(random.uniform(6, 16))
        pole_tekstowe.send_keys(Keys.RETURN)
        # czeka, aż wiadomość się wyśle
        print('napisałem')
        time.sleep(random.uniform(0.5, 1))
        # udawanie człowieka
        time.sleep(random.uniform(2, 4))


def imie_to_imie_w_wolaczu(imie):
    if imie[-1] == 'a':
        if imie in {'Ania', 'Ola', 'Ula'}:
            imie_w_wolaczu = imie[:-1] + 'u'
        else:
            imie_w_wolaczu = imie[:-1] + 'o'
    else:
        imie_w_wolaczu = imie
    return imie_w_wolaczu


# kolejne trzy funkcje dostosowują xpathy w zależności, czy występuje wymuszacz
# tinder golda
def messages_tab_xpath():
    # dostosowuje xpath w zależności, czy ie pojawił się wymuszacz tinder golda
    try:
        driver.find_element_by_xpath('//div[contains(text(), "PIERWSZY MIESIĄC")]')
    except NoSuchElementException:
        return "//nav[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/button[1]"
    else:
        return "//nav[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[2]/button[1]"


def match_tab_xpath():
    # dostosowuje xpath w zależności, czy ie pojawił się wymuszacz tinder golda
    try:
        driver.find_element_by_xpath('//div[contains(text(), "PIERWSZY MIESIĄC")]')
    except NoSuchElementException:
        return "//div[1]/aside[1]/nav[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/button[1]"
    else:
        return "//div[1]/aside[1]/nav[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/button[1]"


def ikonki_xpath():
    try:
        driver.find_element_by_xpath('//div[contains(text(), "PIERWSZY MIESIĄC")]')
    except NoSuchElementException:
        return "//nav[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[.]/div[.]"
    else:
        return "//nav[1]/div[1]/div[1]/div[1]/div[3]/div[1]/div[.]/div[.]"


def odpowiedz_tnd():
    # ewentualnie zamienić na: "//h1[@class='Fz($xl) Fw($bold) Fxs(1) Fxw(w) Pend(8px) M(0) D(i)']"
    imiewiek_xpath = "//main[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[1]/div[1]"
    najnowsza_dziewczyna_xpath = "//aside[1]/nav[1]/div[1]/div[1]/div[1]/div[2]/div[2]/div[2]/a[1]"
    wyslano_zaposzenie_na_spotkanie = False
    # kliknięcie w wiadomości
    driver.find_element_by_xpath(messages_tab_xpath()).click()
    time.sleep(random.uniform(3, 5))
    # budowa listy znaczków nowej wiadomości
    # ciekawostka - używamy tutaj regularnej ekspresji '.', jako że
    # w tym miejscu mogą pojawić się różne liczby
    znaczki_do_pisania = driver.find_elements_by_xpath(
                                        "//a['.']//div[1]//div[1]//div[2]")
    time.sleep(random.uniform(3, 5))
    # pętla przez wszystkie niepisane dziewczyny
    for znaczek in znaczki_do_pisania:
        # kliknięcie w nieodpisaną dziewczynę
        znaczek.click()
        # czekanie, by dane poprzedniej ziewczyny zniknęły
        time.sleep(0.5)
        # czekanie aż się załaduje
        Wait(driver, 60).until(ExpCon.presence_of_element_located((
            By.XPATH, imiewiek_xpath)))
        imiewiek = driver.find_element_by_xpath(imiewiek_xpath).text
        print(imiewiek)
        # szukanie dziewczyny w databazie
        try:
            zapis_w_databazie = sesja.query(TabelaDziewczyn).filter(
                TabelaDziewczyn.imiewiek == imiewiek).all()[0]
            print('jej etap:', zapis_w_databazie.etap)
        except IndexError:
            print('nie ma jej w databazie')
            # coś zrobić w tym miejscu, by dawało znać o napisaniu nieznanej dziewczyny
            continue
        teksty, wyslano_zaposzenie_na_spotkanie = \
            wybor_tekstow_od_etapu(zapis_w_databazie)
        wysylanie_wiadomosci_tnd(teksty)
    return wyslano_zaposzenie_na_spotkanie

def inkrementacja_etapu_laski_i_aktualizacja_czasu_zapisu(
        zapis_w_databazie, ilosc_etapow_do_inkrementcji=1):
    zapis_w_databazie.etap += ilosc_etapow_do_inkrementcji
    zapis_w_databazie.czas_ostaniej_aktywnosci = datetime.now()
    sesja.commit()


def wybor_tekstow_od_etapu(zapis_w_databazie):
    max_etap = 4
    # niepisanie do dziewczyn o maksymalnym etapie
    if zapis_w_databazie.etap == max_etap:
        print('to już finalny etap, wysyłam maila')
        wyslij_email(zapis_w_databazie.imiewiek)
        powiadom.wyslij_powiadomienie_o_dziewczynie(
            zapis_w_databazie.imiewiek)
        inkrementacja_etapu_laski_i_aktualizacja_czasu_zapisu(zapis_w_databazie)
        return [''], False
    elif zapis_w_databazie.etap == 1:
        print('wysyłam tekst z etapu 2')
        return teksty_etap_2(zapis_w_databazie), False
    elif zapis_w_databazie.etap == 2:
        print('wysyłam tekst z etapu 3')
        return teksty_etap_3(zapis_w_databazie), False
    else:
        print('wysyłam tekst z liniowych etapów')
        # True oznacza, że zostało wysłane zaproszenie na spotkanie
        return teksty_do_odp_liniowej(zapis_w_databazie), True


def teksty_do_odp_liniowej(zapis_dziewczyny):
    # zwracamy pojedynczy tekst jako listę z jednym elementem
    # dlatego nie ma [0] na końcu
    print('wybieram odpowiedź liniową')
    wiadomosci = sesja.query(TabelaTekstow).filter(
        TabelaTekstow.etap == zapis_dziewczyny.etap + 1).all()
    inkrementacja_etapu_laski_i_aktualizacja_czasu_zapisu(zapis_dziewczyny)
    return wiadomosci


def teksty_etap_2(zapis_dziewczyny):
    intencje, zainteresowania = analiza_wiadomosci(teksty_od_dziewczyny())
    # dodanie zainteresowań do tagów dziewczyny
    # wiadomości do wysłania
    wiadomosci = []
    zainteresowania_do_dtb = str()
    # dodawanie tekstu z wieloma zainteresowaniami
    if len(zainteresowania) >= 3:
        wiadomosci.append(wyszukaj_wiadomosc(etap=2, tag='multitag'))
    # dodawanie tekstów tematycznych
    for i, zainteresowanie in enumerate(zainteresowania):
        wiadomosci.append(wyszukaj_wiadomosc(etap=2, tag=zainteresowanie))
        zainteresowania_do_dtb += '.'
        zainteresowania_do_dtb += zainteresowanie
        # nie pozwala skomentować więcej niż dwa zainteresowania
        if i == 1:
            break
    # usuwanie kropki z początku
    zainteresowania_do_dtb = zainteresowania_do_dtb[1:]
    # dodanie pojedyńczego zainteresowania do tagów dziewczyny
    if len(zainteresowania) != 0:
        zapis_dziewczyny.tagi = zainteresowania_do_dtb
        sesja.commit()
    # dodawanie tekstu o mnie
    if 'Prosba_opowiedziec_o_sobie' in intencje:
        wiadomosci.append(wyszukaj_wiadomosc(etap=2, tag='o mnie'))
        # dopisanie, że ten tekst już był
        zapis_dziewczyny.uwagi = 'powiedzialem_o_mnie'
        sesja.commit()
    inkrementacja_etapu_laski_i_aktualizacja_czasu_zapisu(zapis_dziewczyny)
    return wiadomosci


def teksty_etap_3(zapis_dziewczyny):
    intencje, zainteresowania = analiza_wiadomosci(teksty_od_dziewczyny())
    # wiadomości do wysłania
    wiadomosci = []
    # try na przypadek braku zapisanych zainteresowań
    try:
        zainteresowania_z_poprzedniej_wiadomosci = zapis_dziewczyny.tagi.split('.')
    except AttributeError:
        zainteresowania_z_poprzedniej_wiadomosci = ['brak']
    print('poprednio miała zainteresowania:',
        zainteresowania_z_poprzedniej_wiadomosci)
    # dodawanie tekstów, wchodzących głębiej w temat
    # jeśli napisała o zainteresowaniu, to go bierzemy
    if zainteresowania != set():
        print('szukam właśnie wymienionego zainteresowania')
        wiadomosci.append(wyszukaj_wiadomosc(etap=3, tag=zainteresowania.pop()))
    # jeśli nie, to z pamięci
    else:
        print('szukam zainteresowania z poprzedniej wiadomości')
        wiadomosci.append(wyszukaj_wiadomosc(
            etap=3, tag=zainteresowania_z_poprzedniej_wiadomosci.pop()))
    # dodawanie tekstu o mnie
    if 'Prosba_opowiedziec_o_sobie' in intencje and zapis_dziewczyny.uwagi != \
            'powiedzialem_o_mnie':
        wiadomosci.append(wyszukaj_wiadomosc(etap=2, tag='o mnie'))
    # rozwinięcie tekstu o mnie
    if 'Prosba_rozwinac_o_zawodzie' in intencje and zapis_dziewczyny.uwagi == \
            'powiedzialem_o_mnie':
        wiadomosci.append(wyszukaj_wiadomosc(etap=3, tag='o mnie'))
    # jeśli spyta o moje szalone rzeczy
    if 'Pytanie_o_szalenstwa' in intencje:
        wiadomosci.append(wyszukaj_wiadomosc(etap=3, tag='szalenstwa'))
    inkrementacja_etapu_laski_i_aktualizacja_czasu_zapisu(zapis_dziewczyny)
    return wiadomosci


def teksty_od_dziewczyny():
    # stosujemy regularną ekspresję (liczby od 0 do 9 w ilości od 1 do 2)
    wiadomosci_xpath = '/html[1]/body[1]/div[1]/div[1]/div[1]/div[1]/main[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div["[0-9]{1,2}"]'
    regex_daty = '[0-9]{2}\.[0-9]{2}\.[0-9]{4}, [0-9]{2}:[0-9]{2}'
    nr_jej_pierwszej_wiadomosci, historia_wiadomosci = \
        znajdz_nr_pierw_wiadomosci(wiadomosci_xpath)
    # separacja jej ostatnich wiadomości
    jej_wiadomosci_obiekty = historia_wiadomosci[nr_jej_pierwszej_wiadomosci:]
    # przerabiamy listę obiektów na listę stringów
    jej_wiadomosci = [wiadomosc.text for wiadomosc in jej_wiadomosci_obiekty]
    # filtracja elementów, zawierających czas pisania
    for wiadomosc in jej_wiadomosci:
        if re.match(regex_daty, wiadomosc) is not None:
            jej_wiadomosci.remove(wiadomosc)
    return jej_wiadomosci


@retry
def znajdz_nr_pierw_wiadomosci(wiadomosci_xpath):
    historia_wiadomosci = driver.find_elements_by_xpath(wiadomosci_xpath)
    # iterowanie po wiadomościach i szukanie początku nowych
    for i, wiadomosc in enumerate(historia_wiadomosci):
        if wiadomosc.text[-7:] == 'Wysłano':
            nr_jej_pierwszej_wiadomosci = i + 1
            break
    # jeśli nie znajdzie wiadomości "wysłano", to wywali błąd "referenced
    # before assignement" na "nr_jej_pierwszej_wiadomosci" i zrobi retraja
    # funkcji
    return nr_jej_pierwszej_wiadomosci, historia_wiadomosci

def analiza_wiadomosci(wiadomosci):
    # dzielenie wiadomości na zdania
    def dzielenie_na_zdania(wiadomosci):
        zdania = []
        for wiadomosc in wiadomosci:
            # poniższy wiersz deszyfruje emotikony
            wiadomosc = demojize(wiadomosc)
            podzielona_wiadomosc = re.split('[.?!\n:;()]', wiadomosc)
            zdania += podzielona_wiadomosc
        # usuwanie zdań, oznaczających uśmieszki
        # oraz wywalanie pystych zdań, by wit nie wywalał błędu
        return [zdanie for zdanie in zdania if 'face' not in zdanie
            and zdanie != '' and zdanie != ' ']

    # przygotowanie pojedyńczych zdań do wysłania
    zdania = dzielenie_na_zdania(wiadomosci)
    zainteresowania = set()
    intencje = set()
    for zdanie in zdania:
        odpowiedz_wit = client_wit.message(zdanie)
        if platform == 'win32':
        # try na przypadek, gdyby odpowiedz nie zawierała intencji
            try:
                intencja = odpowiedz_wit['entities']['intent'][0]['value']
            except KeyError:
                pass
            else:
                intencje.add(intencja)
        elif platform == 'linux':
        # try na przypadek, gdyby odpowiedz nie zawierała intencji
            try:
                intencja = odpowiedz_wit['intents'][0]['name']
            except IndexError:
                pass
            else:
                intencje.add(intencja)


        # try na przypadek, gdyby słownik odpowiedzi nie zawierał zainteresowań
        try:
            # nie możemy bezpośrednio wyciągnąć zainteresowania, jako że wit je
            # wysyła w postaci słowników
            if platform == 'win32':
                slowniki_zainteresowan = odpowiedz_wit[
                    'entities']['zainteresowanie']
            elif platform == 'linux':
                slowniki_zainteresowan = odpowiedz_wit[
                    'entities']['zainteresowanie:zainteresowanie']
            # i teraz wyciągamy zainteresowania ze słowników
            for slownik in slowniki_zainteresowan:
                if int(slownik['confidence']) >= 0.7:
                    zainteresowania.add(slownik['value'])
                else:
                    print(f'nie jestem pewien zainteresowania:{slownik}')
        except KeyError:
            pass
    print(f'inencje:{intencje}, zainteresowania:{zainteresowania}')
    return intencje, zainteresowania


def klikanie_tnd(ilosc_klikniec):
    # kliknięcie w pary (niepisane)
    like_xpath = "//main[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[4]"
    dislike_xpath = "//main[1]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[2]"
    wiek_xpath = "//div[1]/div[3]/div[3]/div[1]/div[1]/div[1]/span[2]"
    iks_polubionej_dziewczyny_xpath = "//*[@class='Sq(24px) P(4px)']"
    wyjscie_z_wymuszacza_superlajka_xpath = "//span[contains(text(),'Nie, dziękuję')]"
    zdjęcie_3_xpath = "//div[3]/div[1]/div[1]/span[3]"
    klikanie(ilosc_klikniec, like_xpath, dislike_xpath, wiek_xpath,
        iks_polubionej_dziewczyny_xpath, wyjscie_z_wymuszacza_superlajka_xpath,
        zdjęcie_3_xpath)


def klikanie(ilosc_klikniec, like_xpath, dislike_xpath, wiek_xpath,
        iks_polubionej_dziewczyny_xpath, wyjscie_z_wymuszacza_superlajka_xpath,
        zdjęcie_3_xpath):
    for _ in range(ilosc_klikniec):
        Wait(driver, 90).until(ExpCon.presence_of_element_located((By.XPATH,
            wiek_xpath)))
        # udawanie człowieka
        time.sleep(random.uniform(0.5, 4))
        wiek = int(driver.find_element_by_xpath(wiek_xpath).text)
        # sprawdzanie, czy dziewczyna ma co najmniej 4 zdjęcia (zmniejszenie
        # ryzyka donosu poprzez klikanie bardziej rozbudowanych dziewczyn)
        try:
            driver.find_element_by_xpath(zdjęcie_3_xpath)
        except NoSuchElementException:
            # znielubić
            driver.find_element_by_xpath(dislike_xpath).click()
            print('znielubiłem')
            continue
        if wiek >= 20:
            # polubić
            driver.find_element_by_xpath(like_xpath).click()
            print('polubiłem')
        else:
            # znielubić
            driver.find_element_by_xpath(dislike_xpath).click()
            print('znielubiłem')
            continue
        # wyjście z pop-upu pary
        try:
            Wait(driver, 5).until(ExpCon.presence_of_element_located((By.XPATH,
                iks_polubionej_dziewczyny_xpath)))
            # udawanie człowieka
            time.sleep(random.uniform(1.5, 3))
            driver.find_element_by_xpath(iks_polubionej_dziewczyny_xpath).click()
        except TimeoutException:
            pass
        # wyjście z pop-upu wymuszacza superlajka
        try:
            Wait(driver, 1).until(ExpCon.presence_of_element_located((
                By.XPATH, wyjscie_z_wymuszacza_superlajka_xpath)))
            # udawanie człowieka
            time.sleep(random.uniform(1.5, 3))
            driver.find_element_by_xpath(
                wyjscie_z_wymuszacza_superlajka_xpath).click()
        except TimeoutException:
            pass


def usuwanie_przeterminowanych_dziewczyn():
    czas_krytyczny = datetime.now() - timedelta(days=4)
    przeterminowane = sesja.query(TabelaDziewczyn).filter(
        TabelaDziewczyn.czas_ostaniej_aktywnosci < czas_krytyczny).all()
    for dziewczyna in przeterminowane:
        sesja.delete(dziewczyna)
        # zobaczyć, czy nie da się tego skopiować w lepszy sposób
        sesja.add(TabelaSmietnikowa(
            imiewiek=dziewczyna.imiewiek,
            etap=dziewczyna.etap, tagi=dziewczyna.tagi, portal=dziewczyna.portal,
            #poczatek=dziewczyna.poczatek,
            czas_ostaniej_aktywnosci=dziewczyna.czas_ostaniej_aktywnosci))
    sesja.commit()
    # piątkowa generacja raportu
    if datetime.now().strftime('%a') == 'Fri':
        generacja_raportu()


def generacja_raportu():
    def obliczanie_wynikow(zeszlotygodniowe, zeszlomiesieczne):
        # przygotowywanie słowników z wynikami
        wyniki_tygodniowe = []
        wyniki_miesieczne = []
        # generacja slowników z wynikami
        # tygodniowe...
        ilosc_na_poprzednim_etapie = 0
        ilosc_na_pierwszym_etapie = len(zeszlotygodniowe)
        for etap in range(5, 0, -1):
            ilosc_na_etapie = ilosc_na_poprzednim_etapie + len([dziewczyna
                    for dziewczyna in zeszlotygodniowe if dziewczyna.etap == etap])
            ilosc_na_poprzednim_etapie = ilosc_na_etapie
            try:
                # do obliczenia sprawności
                sprawnosc = int(ilosc_na_etapie/ilosc_na_pierwszym_etapie*100)
            except ZeroDivisionError:
                sprawnosc = 0
                print('dzielenie przez 0, ustawiam sprawność na 0')
            wyniki_tygodniowe.append((etap, ilosc_na_etapie, sprawnosc))
        # odwracamy listę z powrotem
        wyniki_tygodniowe.reverse()
        # ...i miesięczne
        ilosc_na_poprzednim_etapie = 0
        ilosc_na_pierwszym_etapie = len(zeszlomiesieczne)
        for etap in range(5, 0, -1):
            ilosc_na_etapie = ilosc_na_poprzednim_etapie + len([dziewczyna
                for dziewczyna in zeszlomiesieczne if dziewczyna.etap == etap])
            ilosc_na_poprzednim_etapie = ilosc_na_etapie
            try:
                # do obliczenia sprawności
                sprawnosc = int(ilosc_na_etapie/ilosc_na_pierwszym_etapie*100)
            except ZeroDivisionError:
                sprawnosc = 0
                print('dzielenie przez 0, ustawiam sprawność na 0')
            wyniki_miesieczne.append((etap, ilosc_na_etapie, sprawnosc))
        # odwracamy listę z powrotem
        wyniki_miesieczne.reverse()
        return wyniki_tygodniowe, wyniki_miesieczne

    def zapis_wynikow_do_pliku(wyniki_tygodniowe, wyniki_miesieczne):
        # zapis do pliku
        # x oznacza tworzenie pliku
        siedem_wiersz = cztery_dni_temu.strftime('%d:%m:%Y')
        czenascie_wiersz = jedenascie_dni_temu.strftime('%d:%m:%Y')
        trzydziesci_siedem_wiersz = trzydziesci_cztery_dni_temu.strftime('%d:%m:%Y')
        # otwieramy plik i piszemy, potem zamykamy
        plik = open(datetime.now().strftime('Raporty/wyniki_%d-%m-%Y.txt'), 'x')
        # pamiętać, że na linuxie inny znak końca linii
        plik.write('Wyniki tygodniowe {0}-{1}\n'.format(czenascie_wiersz,
            siedem_wiersz))
        for etap in wyniki_tygodniowe:
            plik.write('Etap {}: {} dziewczyn, sprawność:{}%\n'.format(
                etap[0], etap[1], etap[2]))
        plik.write('\n')
        plik.write('Wyniki miesięczne {0}-{1}\n'.format(trzydziesci_siedem_wiersz,
            siedem_wiersz))
        for etap in wyniki_miesieczne:
            plik.write('Etap {}: {} dziewczyn, sprawność:{}%\n'.format(
                etap[0], etap[1], etap[2]))
        plik.close()

    # funkcja właściwa
    # stałe
    poczatek = TabelaSmietnikowa.poczatek
    cztery_dni_temu = datetime.now() - timedelta(days=4)
    jedenascie_dni_temu = datetime.now() - timedelta(days=11)
    trzydziesci_cztery_dni_temu = datetime.now() - timedelta(days=34)
    # filtracja odpowiednich okresów
    zeszlotygodniowe = sesja.query(TabelaSmietnikowa).filter(
        poczatek > jedenascie_dni_temu, poczatek < cztery_dni_temu).all()
    zeszlomiesieczne = sesja.query(TabelaSmietnikowa).filter(
        poczatek > trzydziesci_cztery_dni_temu, poczatek < cztery_dni_temu).all()
    # dalej już w funkcjach
    wyniki_tygodniowe, wyniki_miesieczne = obliczanie_wynikow(
            zeszlotygodniowe, zeszlomiesieczne)
    zapis_wynikow_do_pliku(wyniki_tygodniowe, wyniki_miesieczne)


def obliczanie_ilosci_dziewczyn_do_pisania():
    # sprawności absolutne na poszczególnych etapach
    # (liczone od tego etapu do końca)
    n1 = 0.05
    n2 = 0.4
    n3 = 0.5
    n4 = 0.6
    n5 = 0.7
    n6plus = 0.8
    # obliczamy potrzebną liczbę dziewczyn do napisania według wzoru:
    # I*n1 + E(Ix*nx) => 2
    # gdzie I -szukana liczba, nx - sprawność na etapie x, Ix - obecna ilość
    # dziewczyn na etapie x, E - znak sumy dla x należy od 2 do 6+
    # 2 jest współczynnikiem bezpieczeństwa
    ilosc = []
    for etap in range(2, 6):
        ilosc.append(len((sesja.query(
            TabelaDziewczyn).filter(TabelaDziewczyn.etap == etap).all())))
    ilosc.append(len((sesja.query(
        TabelaDziewczyn).filter(TabelaDziewczyn.etap >= 6).all())))
    EIxnx = ilosc[0] * n2 + ilosc[1] * n3 + ilosc[2] * n4 + ilosc[3] * n5 \
        + ilosc[4] * n6plus
    I = (2 - EIxnx) / n1
    I_int = int(round(I, 0))
    print(f'napiszę do {I_int}dziewczyn')
    # zaokrąglamy do najbliższej i potem dopiero przekształcamy na inta
    return I_int


wyszukaj_wiadomosc = lambda etap, tag: sesja.query(TabelaTekstow).filter(
    TabelaTekstow.etap == etap, TabelaTekstow.tag == tag).all()[0]

def wyslij_email(imiewiek):
    port = 465
    mail = 'conversatorbot@gmail.com'
    haslo = '123456aB'
    adresat = 'dudnikgrv@gmail.com'
    # SSL kontekst
    context = ssl.create_default_context()
    imie = imiewiek[:-3]
    wiek = imiewiek[-3:]
    tresc = f'Cześć!\n\nChce się z Tobą spotkać {imie}, lat {wiek}. Zaprosiłem na jutro.'.encode('utf-8')
    # logowanie i wysyłanie
    with smtplib.SMTP_SSL('smtp.gmail.com', port, context=context) as server:
        server.login(mail, haslo)
        server.sendmail(mail, adresat, tresc)

'''
def analiza_zaproponowanego_terminu():
    for zdanie in zdania:
        odpowiedz_wit = client_wit.message(zdanie)
        if platform == 'win32':
        # try na przypadek, gdyby odpowiedz nie zawierała intencji
            try:
                data_randki_str = odpowiedz_wit['entities']['datetime'][1]['value'][:10]
            except KeyError:
                pass
            else:
                intencje.add(intencja)
        elif platform == 'linux':
        # try na przypadek, gdyby odpowiedz nie zawierała intencji
            try:
                #intencja = odpowiedz_wit['intents'][0]['name']
            except IndexError:
                pass
            else:
                intencje.add(intencja)
        data_randki_obj = datetime.strptime(data_randki_str, '%Y-%m-%d')
        data_randki_obj.weekday()
'''
