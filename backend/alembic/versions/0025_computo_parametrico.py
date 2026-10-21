"""computo parametrico: grandezze, regole per voce, preset; codici stabili B/C/D

Fase 11 (v3.0). SOLO additivo sullo schema: sette tabelle nuove, nessuna colonna
toccata. Sui dati, tre correzioni di CODICE (mai di prezzo o di quantita'):

  1. le sottocategorie e le voci di B-FINITURE / C-SERRAMENTI / D-PRODOTTI
     ricevono un codice stabile (`B.1`, `B.1.1`...): le regole del computo si
     legano al codice, non all'id ne' alla descrizione (RGL-03). Le coppie sono
     costanti incorporate qui sotto, generate dal seed versionato; si scrive
     solo dove il codice e' ancora NULL.
  2. lo smaltimento macerie, che nel seed condivideva il codice `A.9.5` con
     l'assistenza per gli air zone, diventa `A.9.6` (come nel computo Excel
     2025): con due voci sullo stesso codice l'upsert del seed sovrascriveva
     l'una con l'altra.
  3. `A.12.1.` perde il punto finale.

Le tabelle nuove partono vuote: le popola il seed create-if-missing al boot
(D-41), come per gli effetti del catalogo domande.

Revision ID: 0025
Revises: 0024
Create Date: 2026-10-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0025'
down_revision: Union[str, Sequence[str], None] = '0024'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (categoria_code, nome sottocategoria, codice)
_SOTTOCATEGORIE: tuple[tuple[str, str, str], ...] = (
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'B.1'),
    ('B-FINITURE', 'PAVIMENTI', 'B.2'),
    ('B-FINITURE', 'PAVIMENTI PARQUET', 'B.3'),
    ('B-FINITURE', 'BATTISCOPA', 'B.4'),
    ('B-FINITURE', 'MATERIALI DI POSA', 'B.5'),
    ('B-FINITURE', 'RUBINETTERIE', 'B.6'),
    ('C-SERRAMENTI', 'PORTE', 'C.1'),
    ('D-PRODOTTI', 'PRODOTTI', 'D.1'),
)

# (categoria_code, nome sottocategoria, descrizione voce, codice)
_VOCI: tuple[tuple[str, str, str, str], ...] = (
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A):30 × 60 cm, naturale o bocciardato, spessore 10', 'B.1.1'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A): 60 × 60 cm, spessore 15 mm', 'B.1.2'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: effetto cemento, con superficie antiscivolo (R10 A): 60 × 120 cm, naturale, spessore 10 mm', 'B.1.3'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 30 × 30 cm, disegno mosaico', 'B.1.4'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm:30 × 60 cm', 'B.1.5'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Fornitura di pavimentazione/rivestimento in gres porcelanato TIPO: Padana marmosmart pietrasanta smart honed 60 x 60 1° sc. (mq. 1,44x)', 'B.1.6'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:effetto cemento, con superficie antiscivolo (R10 A):dimensioni 60 × 60 cm, spessore 15 mm', 'B.1.7'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm:60 × 120 cm', 'B.1.8'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:effetto cemento, con superficie antiscivolo (R10 A):60 × 120 cm, naturale, spessore 10 mm', 'B.1.9'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 30 × 60 cm, spessore 10 mm', 'B.1.10'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto pietra naturale, rettificato, antiscivolo (R9): 60 × 120 cm, spessore 10,5 mm', 'B.1.11'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: granigliato: 30 × 30 cm, effetto marmetta grana media antiscivolo (R11), spessore 8,5 mm', 'B.1.12'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL: granigliato: 30 × 30 cm, superficie bocciardata antiscivolo (R12 B), spessore 8,5 mm', 'B.1.13'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto pietra naturale, rettificato, antiscivolo (R9):60 × 120 cm, spessore 10,5 mm', 'B.1.14'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto pietra naturale, rettificato, antiscivolo (R9): 60 × 60 cm, spessore 10 mm', 'B.1.15'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL: effetto cemento:120 × 120 cm, rettificato, spessore 10,5 mm', 'B.1.16'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa, ottenuto per pressatura, in lastre di bassissimo spessore rinforzate sul lato inferiore con rete in fibra di vetro, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe reazione al fuoco A2 - s1, classe assorbimento acqua Bia-UGL, ', 'B.1.17'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato smaltato in piastrelle, resistente agli sbalzi termici, al gelo e agli acidi, per pavimentazioni ad uso residenziale o terziario leggero, a norma UNI EN 14411 gruppo BIa GL:effetto marmo, antiscivolo (R9), spessore 9 mm: 90 × 90 cm', 'B.1.18'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:120 × 278 cm, spessore 6 mm:effetto marmo, superficie lucida', 'B.1.19'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Gres porcellanato colorato in massa in piastrelle rettificate, ottenute per pressatura, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe assorbimento acqua BIa UGL:160 × 320 cm, spessore 6 mm:effetto marmo, superficie lucida', 'B.1.20'),
    ('B-FINITURE', 'PAVIMENTI E RIVESTIMENTI GRES', 'Ceramica monocottura di pasta bianca in lastre ottenute per pressatura, rettificate, per rivestimenti ad uso residenziale, grado di assorbimento acqua gruppo BIII L a norma UNI EN 14411, delle dimensioni di 60 × 180 cm:effetto cemento, strutturato, spessore 9 mm', 'B.1.21'),
    ('B-FINITURE', 'PAVIMENTI', 'Gres porcellanato colorato in massa, ottenuto per pressatura, in lastre di bassissimo spessore rinforzate sul lato inferiore con rete in fibra di vetro, per pavimentazioni ad intenso calpestio, rispondenti alla norma UNI EN 14411, classe reazione al fuoco A2 - s1, classe assorbimento acqua Bia-UGL, ', 'B.2.1'),
    ('B-FINITURE', 'PAVIMENTI', "Vinilico multistrato LVT in listoni delle dimensioni di 17 ÷ 20 × 100 ÷ 124 cm o piastre delle dimensioni di 36 × 69 cm con profili laterali ad incastro per posa senza collante, con uno strato d'usura in pvc puro trasparente che protegge uno strato a motivi stampatitrattato con fotoreticolazione UV ", 'B.2.2'),
    ('B-FINITURE', 'PAVIMENTI', "Pavimento in laminato antistatico (< 2 kV - UNI EN 1815 ed UNI EN 14041), con supporto di base in fibra di legno ad elevata densità (HDF) con superficie ad effetto legno, resistenza all'abrasione superficiale in classe AC4 (UNI EN 13329), rigonfiamento del bordo ≤ 18% (valore medio 11% UNI EN 13329)", 'B.2.3'),
    ('B-FINITURE', 'PAVIMENTI', 'Unilin sottofondo in schiuma senza barriera vapore', 'B.2.4'),
    ('B-FINITURE', 'PAVIMENTI', 'Tesserine di vetro per pavimenti a tinta unita delle dimensioni 2 × 2 cm, spessore 4 cm, premontate su fogli di carta dimensioni 30 × 30 cm:colori medi', 'B.2.5'),
    ('B-FINITURE', 'PAVIMENTI', 'Moquette in quadrotte autoposanti idonee alla posa senza collante, ad alta flessibilità, antistatiche, ignifughe di classe 1, dimensioni 50 × 50 cm: con supporto in composto termoplastico rinforzato con due strati di fibre di vetro e pretrattato con antibatterico:100% nylon, superficie velluto diseg', 'B.2.6'),
    ('B-FINITURE', 'PAVIMENTI PARQUET', 'Parquet prefinito in listoni composti da uno strato superiore in legno nobile di spessore 5 mm e supporto in multistrato di betulla con profili maschiati:con superficie prelevigata, da finire in opera, spessore totale 14 mm, lunghezza 1.200 ÷ 2.000 mm, larghezza 140 mm:rovere', 'B.3.1'),
    ('B-FINITURE', 'PAVIMENTI PARQUET', 'Parquet prefinito in listoni composti da uno strato superiore in legno nobile di spessore 5 mm e supporto in multistrato di betulla con profili maschiati:con superficie prelevigata, da finire in opera, spessore totale 10mm, lunghezza 1.200 ÷ 2.000 mm, larghezza 140 mm:rovere', 'B.3.2'),
    ('B-FINITURE', 'PAVIMENTI PARQUET', 'Parquet prefinito in listoni composti da uno strato superiore in legno nobile di spessore 5 mm e supporto in multistrato di betulla con profili maschiati:con superficie prelevigata, da finire in opera, spessore totale 14 mm, lunghezza 1.200 ÷ 2.000 mm, larghezza 140 mm: teak', 'B.3.3'),
    ('B-FINITURE', 'PAVIMENTI PARQUET', 'Parquet prefinito in listoni composti da uno strato superiore in legno nobile di spessore 5 mm e supporto in multistrato di betulla con profili maschiati:con superficie prelevigata, da finire in opera, spessore totale 14 mm, lunghezza 1.200 ÷ 2.000 mm, larghezza 140 mm: iroko', 'B.3.4'),
    ('B-FINITURE', 'PAVIMENTI PARQUET', 'Parquet prefinito in listoni composti da uno strato superiore in legno nobile di spessore 5 mm e supporto in multistrato di betulla con profili maschiati:con superficie prelevigata, da finire in opera, spessore totale 14 mm, lunghezza 1.200 ÷ 2.000 mm, larghezza 140 mm: rovere', 'B.3.5'),
    ('B-FINITURE', 'PAVIMENTI PARQUET', 'Parquet prefinito in listoni composti da uno strato superiore in legno nobile di spessore 5 mm e supporto in multistrato di betulla con profili maschiati:con superficie prelevigata, da finire in opera, spessore totale 14 mm, lunghezza 1.200 ÷ 2.000 mm, larghezza 140 mm: wengè', 'B.3.6'),
    ('B-FINITURE', 'BATTISCOPA', 'Zoccolino di gres porcellanato colorato in massa, superficie naturale o bocciardata:effetto cemento, 10 × 30 cm, spessore 8,5 mm con sguscia', 'B.4.1'),
    ('B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 75 × 10 mm: essenza', 'B.4.2'),
    ('B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 75 × 10 mm: multistrato bianco', 'B.4.3'),
    ('B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 40 × 10 mm: multistrato bianco', 'B.4.4'),
    ('B-FINITURE', 'BATTISCOPA', 'Zoccolino in legno 40 × 10 mm: essenza', 'B.4.5'),
    ('B-FINITURE', 'MATERIALI DI POSA', 'Colle, stucchi distanziatori e cunei per la posa', 'B.5.1'),
    ('B-FINITURE', 'RUBINETTERIE', 'Miscelatore monocomando cromato per lavabo con scarico automatico: normale', 'B.6.1'),
    ('B-FINITURE', 'RUBINETTERIE', 'Miscelatore monocomando cromato per bidet, erogazione a doccetta orientabile, completo di scarico, senza nipples e rosoni', 'B.6.2'),
    ('B-FINITURE', 'RUBINETTERIE', 'Miscelatore cromato monocomando da incasso per doccia/vasca: con corpo incassato, maniglia, cappuccio, rosone, doccia a sistema anticalcare, flessibile da 1500 mm e appendidoccia orientabile.', 'B.6.3'),
    ('B-FINITURE', 'RUBINETTERIE', 'Piatto doccia in acrilico colore bianco, scarico centrale, per installazione sopra pavimento, inclusa piletta sifonata con foro ∅ 90 mm: rettangolare: 120 × 80 × 4 cm o 100 × 80 × 4 cm', 'B.6.4'),
    ('B-FINITURE', 'RUBINETTERIE', 'Vasca in acrilico colore bianco, scarico centrale, per installazione ad incasso, inclusa piletta sifonata con foro ∅ 90 mm: rettangolare: 170 × 70', 'B.6.5'),
    ('B-FINITURE', 'RUBINETTERIE', "Cabina per piatto doccia composta da porta con profili in alluminio verniciato a caldo con resine epossidiche, altezza 1850 mm, lastre trasparenti con guarnizioni in gomma trattate con antimuffa, chiusura anta apribile mediante magnete:una porta a soffietto con apertura verso l'interno, con vetro st", 'B.6.6'),
    ('B-FINITURE', 'RUBINETTERIE', 'Bidet in porcellana dura (vetrochina): monoforo con erogazione dalla rubinetteria, 36 × 54 × 39 cm', 'B.6.7'),
    ('B-FINITURE', 'RUBINETTERIE', 'Vaso igienico in porcellana vetrificata (vetrochina), esclusi accessori di fissaggio: scarico a pavimento', 'B.6.8'),
    ('B-FINITURE', 'RUBINETTERIE', 'Vaso igienico in porcellana vetrificata (vetrochina), esclusi accessori di fissaggio: sospeso con scarico a parete', 'B.6.9'),
    ('B-FINITURE', 'RUBINETTERIE', 'Bidet in porcellana dura (vetrochina): sospeso, monoforo con erogazione dalla rubinetteria. 35 × 57 × 32 cm', 'B.6.10'),
    ('B-FINITURE', 'RUBINETTERIE', 'Cassetta d\'incasso da 9 litri, per posa in muratura, con regolazione del flusso e doppio tipo di risciacquo, allacciamento alla rete idrica sul lato superiore da 1/2", con rubinetto d\'arresto, fissaggi per la cassetta e rete di rivestimento per l\'intonaco, con tubo di risciacquamento in polietilene ', 'B.6.11'),
    ('B-FINITURE', 'RUBINETTERIE', "Placca di copertura per cassette d'incasso: con tasto di comando e interruzione del risciacquo, in materiale plastico opaca", 'B.6.12'),
    ('B-FINITURE', 'RUBINETTERIE', 'Radiatore a rastrelliera realizzato con tubolari orizzontali in acciaio preverniciato con polveri epossidiche a finire di colore bianco, attacchi ∅ 1/2", pressione d\'esercizio 8 bar, temperatura massima d\'esercizio 95 °C, resa termica con Δ Ti di 50 °C secondo UNI EN 442, in opera compresi valvola t', 'B.6.13'),
    ('B-FINITURE', 'RUBINETTERIE', "Radiatori in alluminio ad elementi componibili profondità 95 ÷ 100 mm, preverniciati al forno con polveri epossidiche preassemblati mediante nipples in acciaio, emiss. termica con Δ T50 °C secondo norme UNI EN 442, dati in opera completi di valvola d'intercettazione e detentore, valvola sfogo aria, ", 'B.6.14'),
    ('C-SERRAMENTI', 'PORTE', 'Porta interna in legno con anta mobile tamburata e con bordi impiallacciati, completa di telaio maestro in listellare impiallacciato dello spessore di 8/11 mm, coprifili ad incastro in multistrato e tutta la ferramenta necessaria per il fissaggio, movimento e chiusura, delle dimensioni standard di 2', 'C.1.1'),
    ('C-SERRAMENTI', 'PORTE', 'Montaggio di porte interne a battente misure standard', 'C.1.2'),
    ('C-SERRAMENTI', 'PORTE', 'Porta in legno scorrevole interno muro con anta tamburata e bordi impiallacciati, spessore 8/11 mm, coprifili ad incastro in multistrato, serratura a gancio con nottolino e maniglia ad incasso, dimensioni 210 × 60 ÷ 90 cm:cieca liscia, anta singola:noce tanganika', 'C.1.3'),
    ('C-SERRAMENTI', 'PORTE', 'Porta in legno scorrevole interno muro con anta tamburata e bordi impiallacciati, spessore 8/11 mm, coprifili ad incastro in multistrato, serratura a gancio con nottolino e maniglia ad incasso, dimensioni 210 × 60 ÷ 90 cm:cieca liscia, anta singola:laccata bianca', 'C.1.4'),
    ('C-SERRAMENTI', 'PORTE', 'Montaggio di porte interne a scomparsa misure standard', 'C.1.5'),
    ('C-SERRAMENTI', 'PORTE', "Porta blindata costituita da telaio in lamiera d'acciaio dello spessore di 20/10 verniciato e predisposto per l'ancoraggio dei bulloni, controtelaio in lamiera dello spessore di 25/10 verniciato con vernice antiruggine, anta in doppia lamiera d'acciaio dello spessore di 12/10 con profili perimetrali", 'C.1.6'),
    ('C-SERRAMENTI', 'PORTE', 'Rimozione vecchio controtelaio e ripristino delle parti ammalorate mediante stuccatura e verciatura delle parti interessate', 'C.1.7'),
    ('C-SERRAMENTI', 'PORTE', 'Montaggio di porta blindata mediante montaggio di nuovo controtelaio e assistenza muraria', 'C.1.8'),
    ('C-SERRAMENTI', 'PORTE', 'Finestre a 1/2/3 ante con profilo in PVC , telaio SL LA, colore bianco massa, (5 camere con doppia guarnizione), doppio rinforzo, comprensivo di vetro di sicurezza 2.2.1-18GA-22.1BE. Completo di anta a ribalta, microventilazione, ferramenta e maniglia satinata. La voce comprende fornitura, trasporto', 'C.1.9'),
    ('C-SERRAMENTI', 'PORTE', 'Porta finestra a 1/2/3 ante con profilo in PVC , telaio SL LA, colore bianco massa, (5 camere con doppia guarnizione), doppio rinforzo, comprensivo di vetro di sicurezza 2.2.1-18GA-22.1BE. Completo di anta a ribalta, microventilazione, ferramenta e maniglia satinata. La voce comprende fornitura, tra', 'C.1.10'),
    ('C-SERRAMENTI', 'PORTE', 'Tapparelle in PVC effetto legno. La voce comprende fornitura, trasporto e montaggio  con smontaggio delle vecchie tapparelle e scarico su fronte strada.  Compreso il carico da piano strada e trasporto ad impianti di stoccaggio, di recupero o a discarica. NB:il prezzo è da considerarsi puramente indi', 'C.1.11'),
    ('C-SERRAMENTI', 'PORTE', 'Tapparelle in alluminio effetto legno. La voce comprende fornitura, trasporto e montaggio  con smontaggio delle vecchie tapparelle e scarico su fronte strada.  Compreso il carico da piano strada e trasporto ad impianti di stoccaggio, di recupero o a discarica. NB:il prezzo è da considerarsi purament', 'C.1.12'),
    ('C-SERRAMENTI', 'PORTE', 'Cassonetti coibentati in PVC colore a scelta. La voce comprende fornitura, trasporto e montaggio  con smontaggio dei vecchi cassonetti e scarico su fronte strada.  Compreso il carico da piano strada e trasporto ad impianti di stoccaggio, di recupero o a discarica. NB:il prezzo è da considerarsi pura', 'C.1.13'),
    ('C-SERRAMENTI', 'PORTE', 'Zanzariere a molla orizzontale e/o a catena e/o scorrevole e/o zanzariera a battente. La voce comprende fornitura, trasporto e montaggio NB:il prezzo è da considerarsi puramente indicativo in quanto andrà confermato previo sopralluogo del serramentista e dopo la scelta della tipologia adatta alle pr', 'C.1.14'),
    ('D-PRODOTTI', 'PRODOTTI', 'Fornitura di condizionatore SAMSUNG CEBU monoplit', 'D.1.1'),
    ('D-PRODOTTI', 'PRODOTTI', 'Fornitura di condizionatore SAMSUNG CEBU dualsplit', 'D.1.2'),
    ('D-PRODOTTI', 'PRODOTTI', 'Fornitura di condizionatore SAMSUNG CEBU trialsplit', 'D.1.3'),
    ('D-PRODOTTI', 'PRODOTTI', 'Fornitura di condizionatore DAIKIN PREFERA monoplit', 'D.1.4'),
    ('D-PRODOTTI', 'PRODOTTI', 'Fornitura di condizionatore DAIKIN PREFERA dualsplit', 'D.1.5'),
    ('D-PRODOTTI', 'PRODOTTI', 'Fornitura di condizionatore DAIKIN PREFERA trialsplit', 'D.1.6'),
    ('D-PRODOTTI', 'PRODOTTI', 'Fornitura Caldaia MYNUTE RAIN GREEN E 25', 'D.1.7'),
    ('D-PRODOTTI', 'PRODOTTI', 'Fornitura scaldabagno TURBO 12L', 'D.1.8'),
    ('D-PRODOTTI', 'PRODOTTI', 'Fornitura di termosifoni tubolari NOVO 1520/500', 'D.1.9'),
    ('D-PRODOTTI', 'PRODOTTI', 'Fornitura scaldasalviette NOVO', 'D.1.10'),
)


def _timestamp() -> sa.Column:
    return sa.Column(
        "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
    )


def upgrade() -> None:
    op.create_table(
        "grandezza",
        sa.Column("code", sa.String(48), primary_key=True),
        sa.Column("nome", sa.String(200), nullable=False),
        sa.Column("um", sa.String(16), nullable=False, server_default=""),
        sa.Column("descrizione", sa.String(500), nullable=True),
        sa.Column("ordine", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("costante", sa.Numeric(12, 4), nullable=False, server_default="0"),
        sa.Column("da_attesa", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("arrotondamento", sa.String(8), nullable=False, server_default="nessuno"),
        sa.Column("minimo", sa.Numeric(12, 4), nullable=True),
        sa.Column("massimo", sa.Numeric(12, 4), nullable=True),
        sa.Column("attiva", sa.Boolean(), nullable=False, server_default="1"),
        _timestamp(),
    )
    op.create_table(
        "termine_grandezza",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "grandezza_code",
            sa.String(48),
            sa.ForeignKey("grandezza.code", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sorgente_code", sa.String(48), nullable=False),
        sa.Column("fattore", sa.Numeric(12, 4), nullable=False),
        sa.Column("per_grandezza_code", sa.String(48), nullable=True),
        sa.Column("ordine", sa.Integer(), nullable=False, server_default="0"),
        _timestamp(),
    )
    op.create_table(
        "valore_grandezza_opzione",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "opzione_id",
            sa.Integer(),
            sa.ForeignKey("opzione_domanda.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "grandezza_code",
            sa.String(48),
            sa.ForeignKey("grandezza.code", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("valore", sa.Numeric(12, 4), nullable=False),
        _timestamp(),
        sa.UniqueConstraint("opzione_id", "grandezza_code", name="uq_valore_grandezza_opzione"),
    )
    op.create_table(
        "regola_voce",
        sa.Column("voce_codice", sa.String(32), primary_key=True),
        sa.Column("tipo_regola", sa.String(32), nullable=False),
        sa.Column("grandezza_code", sa.String(48), nullable=True),
        sa.Column("fattore", sa.Numeric(12, 4), nullable=False, server_default="1"),
        sa.Column("condizione_grandezza_code", sa.String(48), nullable=True),
        sa.Column("importo_minimo", sa.Numeric(12, 2), nullable=True),
        sa.Column("nota", sa.String(500), nullable=True),
        sa.Column("attiva", sa.Boolean(), nullable=False, server_default="1"),
        _timestamp(),
    )
    op.create_table(
        "sorgente_regola",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "voce_codice",
            sa.String(32),
            sa.ForeignKey("regola_voce.voce_codice", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sorgente_codice", sa.String(32), nullable=False),
        _timestamp(),
        sa.UniqueConstraint("voce_codice", "sorgente_codice", name="uq_sorgente_regola"),
    )
    op.create_table(
        "scaglione_regola",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "voce_codice",
            sa.String(32),
            sa.ForeignKey("regola_voce.voce_codice", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fino_a", sa.Numeric(12, 4), nullable=True),
        sa.Column("valore", sa.Numeric(12, 4), nullable=False),
        _timestamp(),
    )
    op.create_table(
        "preset_risposta",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "tipo_code",
            sa.String(32),
            sa.ForeignKey("tipo_ristrutturazione.code"),
            nullable=False,
        ),
        sa.Column(
            "domanda_code",
            sa.String(64),
            sa.ForeignKey("domanda.code", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("opzione_code", sa.String(64), nullable=True),
        sa.Column("valore", sa.Numeric(12, 4), nullable=True),
        _timestamp(),
        sa.UniqueConstraint("tipo_code", "domanda_code", "opzione_code", name="uq_preset_risposta"),
    )

    bind = op.get_bind()
    sottocategoria = sa.table(
        "sottocategoria",
        sa.column("id", sa.Integer),
        sa.column("categoria_code", sa.String),
        sa.column("codice", sa.String),
        sa.column("nome", sa.String),
    )
    voce = sa.table(
        "voce",
        sa.column("id", sa.Integer),
        sa.column("sottocategoria_id", sa.Integer),
        sa.column("codice", sa.String),
        sa.column("descrizione", sa.String),
    )

    for categoria_code, nome, codice in _SOTTOCATEGORIE:
        bind.execute(
            sottocategoria.update()
            .where(
                sottocategoria.c.categoria_code == categoria_code,
                sottocategoria.c.nome == nome,
                sottocategoria.c.codice.is_(None),
            )
            .values(codice=codice)
        )

    for categoria_code, nome, descrizione, codice in _VOCI:
        sotto_ids = sa.select(sottocategoria.c.id).where(
            sottocategoria.c.categoria_code == categoria_code,
            sottocategoria.c.nome == nome,
        )
        bind.execute(
            voce.update()
            .where(
                voce.c.sottocategoria_id.in_(sotto_ids),
                voce.c.descrizione == descrizione,
                voce.c.codice.is_(None),
            )
            .values(codice=codice)
        )

    bind.execute(
        voce.update()
        .where(voce.c.codice == "A.9.5", voce.c.descrizione.like("Smaltimento%"))
        .values(codice="A.9.6")
    )
    bind.execute(voce.update().where(voce.c.codice == "A.12.1.").values(codice="A.12.1"))


def downgrade() -> None:
    bind = op.get_bind()
    voce = sa.table("voce", sa.column("codice", sa.String), sa.column("descrizione", sa.String))
    bind.execute(voce.update().where(voce.c.codice == "A.12.1").values(codice="A.12.1."))
    bind.execute(voce.update().where(voce.c.codice == "A.9.6").values(codice="A.9.5"))
    for prefisso in ("B.", "C.", "D."):
        bind.execute(voce.update().where(voce.c.codice.like(prefisso + "%")).values(codice=None))
        sottocategoria = sa.table("sottocategoria", sa.column("codice", sa.String))
        bind.execute(
            sottocategoria.update()
            .where(sottocategoria.c.codice.like(prefisso + "%"))
            .values(codice=None)
        )
    for tabella in (
        "preset_risposta",
        "scaglione_regola",
        "sorgente_regola",
        "regola_voce",
        "valore_grandezza_opzione",
        "termine_grandezza",
        "grandezza",
    ):
        op.drop_table(tabella)
