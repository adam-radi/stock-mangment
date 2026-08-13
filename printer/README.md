# Module Impression — WDLink WD8260 (USB, 80 mm)

Ce dossier isole toute la logique d'impression thermique, pour que le
reste de l'application (produits, stock, ventes) fonctionne **même si
l'imprimante n'est pas branchée ou pas détectée**.

## Fonctionnement

```
Web App (navigateur)
       ↓
Backend Flask (app.py)  →  POST /api/print/<sale_id>
       ↓
printer/printer.py  (service d'impression local)
       ↓
WDLink WD8260 (USB, ESC/POS)
```

Si l'imprimante n'est pas accessible, `printer.py` ne fait planter ni
la vente ni l'application : il renvoie simplement un ticket texte que
vous pouvez afficher / imprimer manuellement depuis le navigateur
(Ctrl+P) ou copier vers l'imprimante en mode texte brut.

## 1. Installer la librairie d'impression (recommandé)

Sur le PC Windows 10, dans l'environnement Python de l'application :

```
pip install python-escpos pyusb
```

`python-escpos` sait parler le protocole ESC/POS utilisé par la
majorité des imprimantes thermiques 80 mm, y compris la WD8260.

`pyusb` a besoin d'un pilote USB générique (libusb). Sous Windows 10,
le plus simple est d'utiliser **Zadig** :

1. Téléchargez Zadig (https://zadig.akeo.ie/) sur le PC cible.
2. Branchez la WD8260 en USB, mettez-la sous tension.
3. Lancez Zadig → "Options" → "List All Devices".
4. Sélectionnez la WD8260 dans la liste déroulante.
5. Choisissez le pilote **WinUSB** (ou libusb-win32) et cliquez sur
   "Install Driver" / "Replace Driver".

## 2. Identifier l'imprimante (Vendor ID / Product ID)

1. Branchez la WD8260, ouvrez le Gestionnaire de périphériques Windows.
2. Repérez l'imprimante (souvent sous "Périphériques USB" ou
   "Contrôleurs de bus USB").
3. Clic droit → Propriétés → onglet "Détails" → propriété
   "ID matériel". Vous verrez quelque chose comme :
   `USB\VID_0483&PID_5743&...`
   - `VID_0483` → Vendor ID = `0x0483`
   - `PID_5743` → Product ID = `0x5743`
4. Ouvrez `printer/printer.py` et mettez à jour, si besoin :

```python
PRINTER_VENDOR_ID = "0x0483"
PRINTER_PRODUCT_ID = "0x5743"
```

   (ou définissez les variables d'environnement `WD8260_VENDOR_ID` /
   `WD8260_PRODUCT_ID` avant de lancer `start.bat`).

## 3. Tester l'impression

1. Lancez l'application (`start.bat`).
2. Connectez-vous, allez dans **Paramètres** : le statut doit afficher
   "Printer connected" si la détection automatique fonctionne, sinon
   "Printer not detected" (l'application continue de fonctionner
   normalement dans ce cas).
3. Faites une vente de test, cliquez sur **Imprimer**.
4. Si l'imprimante ne réagit pas :
   - vérifiez le câble USB et l'alimentation,
   - vérifiez le pilote (WinUSB via Zadig),
   - vérifiez le Vendor ID / Product ID,
   - en dernier recours, utilisez le bouton **"Aperçu / Imprimer via
     navigateur"** sur la page du reçu : le ticket s'affiche formaté
     pour 80 mm et peut être imprimé avec Ctrl+P vers l'imprimante
     installée comme imprimante Windows classique.

## 4. Mode de secours (sans python-escpos)

Si `python-escpos` n'est pas installé ou que l'imprimante n'est pas
détectable, `printer.py` génère automatiquement un ticket texte
(largeur 42 caractères, adapté au papier 80 mm) qui est renvoyé à
l'application web et affiché à l'écran pour impression manuelle.
Aucune fonctionnalité de vente n'est bloquée par ce mode.
