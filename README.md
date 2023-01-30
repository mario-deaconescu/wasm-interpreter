# WASM-INTERPRETER
 Proiect realizat de:
 
    - Deaconescu Sabin Mario, grupa 151
    - Preda Maria, grupa 151
    - Miu Tudor, grupa 151
    - Berbece David-Constantin, grupa 151
  ## Instalare
  
  - Pentru a interpreta, rulam ```interpreter.py``` avand drept parametru numele fisierului pe care dorim sa-l interpretam.
  - Programul ruleaza pentru Python 3.10 si versiuni ulterioare.
  
  ## Cum functioneaza
  
  - Fisierul ```interpreter.py``` citeste expresiile, cu ajutorul functiei ```read_expressions```, care scoate comentariile, (';; ...' si '\n', iar in loc de mai multe spatii se pune unul singur), folosind regex.
      - Dupa aceea, cu ajutorul parantezelor, functia se apeleaza recursiv pentru a crea un arbore in care radacina este ```module```, 
      avand drept fii denumirile functiilor care sunt de interpretat, toate aceastea avand drept fii parametrii, si body-ul...etc. Un exemplu simplificat de un 
      astfel de arbore este:

![graph (3)
](https://user-images.githubusercontent.com/115883033/215325914-852ace40-622c-48a2-ac11-9b0de49ec2b7.png)

M=Module
F=Functie
I=Instructiune
P= Parametru

     - Functia ```check_asserts``` verifica asserturile, acestea fiind de 4 tipuri:

          - Invalid, daca este eroare structurala
          - Return, ce verifica rezultatul unor instructiuni
          - Trap, daca functia returneaza un anumit tip de eroare
          - Malformed, care verifica sintaxa

  ## Structura POO

  - Fisierul ```instantiate.py``` parseaza si, cu ajutorul unui dictionar, trece din 
  srtringul expresiei intr-o clasa corespunzatoare
  - Fisierul ```operations.py``` defineste clasele pentru operatii (adunare, scadere,
  inmultire, impartire cu/fara semn, etc.). Functiile din clase verifica eventualele 
  erori si fac operatiile necesare.
  - Fisierele auxiliare definesc alte tipuri de expresii precum cele logice (```logic.py```), cele cu operatii pe stiva (```stackoperations.py```), etc.

  Clasa de baza din care este mostenita fiecare expresie este ```SExpression```, iar o alta subclasa importanta este ```Evaluation```, din care mosteneste fiecare expresie care poate fi "evaluata" (adica este o instructiune care poate fi rulata)

  O vizualizare a acestui "arbore" de mosteniri se poate vedea mai jos (pentru a vedea mai usor, este recomandat sa descarcati poza si sa dati zoom, pentru ca aveam multe clase asemanatoare care mnostenesc din aceeasi clasa parinte):
  
![graph (1)](https://user-images.githubusercontent.com/65511514/215580516-68b0da2d-2911-4ba3-b224-2a479403a177.png)

  ## Output
    - La rularea programului, se va afisa pe ecran:
      
        - Numarul fiecarei expresie de tip assert, tipul ei, si daca a fost evaluata corect
        - Eroare de tip "Not implemented" daca o expresie nu a fost implementata