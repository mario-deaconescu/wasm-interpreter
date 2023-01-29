# WASM-INTERPRETER
 Proiect realizat de:
 
    - Deaconescu Sabin Mario, grupa 151
    - Preda Maria, grupa 151
    - Miu Tudor, grupa 151
    - Berbece David-Constantin, grupa 151
  ## Instalare
  
  - Pentru a interpreta, rulam ```interpreter.py``` avand drept parametru numele fisierului pe care dorim sa-l interpretam.
  - Ultima versiune de Python pentru care proiectul ruleaza este Python 3.10
  
  ## Cum functioneaza
  
  - Fisierul ```interpreter.py``` citeste expresiile, cu ajutorul functiei ```read_expressions```, care scoate comentariile, (';.*' si '\n', iar in loc de '+' se pune spatiu )
      - Dupa aceea, cu ajutorul parantezelor, functia se apeleaza recursiv pentru a crea un arbore in care radacina este ```module```, 
      avand drept fii denumirile functiilor care sunt de interpretat, toate aceastea avand drept fii parametrii, erorile si body-ul...etc. Un exemplu simplificat de un 
      astfel de graf este:

![graph (3)
](https://user-images.githubusercontent.com/115883033/215325914-852ace40-622c-48a2-ac11-9b0de49ec2b7.png)

M=Module
F=Functie
I=Instructiune
P= Parametru

     - Functia ```check_asserts``` verifica asserturile, acestea fiind de 4 tipuri:

          - Invalid, daca este eroare de sintaxa
          - Return, ce returneaza functia
          - Trap, daca functia returneaza un anumit tip de eroare
          - Malformed, care verifica sintaxa

  - Fisierul ```instantiate.py``` parseaza, cu ajutorul unui dictionar, trece din 
  srtringul expresiei intr-o clasa corespunzatoare
  - Fisierul ```operations.py``` defineste clasele pentru operatii (adunare, scadere,
  inmultire, impartire cu/fara semn). Functiile din clase verifica eventualele 
  erori si fac operatiile necesare.
  - Fisierul ```expressions.py``` nu stiu cplm mai face
  
