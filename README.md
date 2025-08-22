# PicarxAngularController

This project was generated using [Angular CLI](https://github.com/angular/angular-cli) version 20.1.3.

## Development server

To start a local development server, run:

```bash
ng serve
```
<small> Once the server is running, open your browser and navigate to `http://localhost:4200/`. The application will automatically reload whenever you modify any of the source files.

---
# Setting Up PiCar-X Python Environment with Websockets

Follow these steps to create a fresh Python virtual environment for PiCar-X, install the required packages, and run the WebSocket server.

---

## Step 1: Create a New Virtual Envrionment with System Packages

This allows the venv to access globally installed packages (like robothat)

```bash
python3 -m venv --system-site-packages ~/picar-x/venv
```
## Step 2: Activate the Virtual Environment
```bash
source ~/picar-x/venv/bin/activate
```
## Step 3: Install Required Python Packages
If you need Flask, install it as well
```bash
pip install websockets
pip install flask
pip install pygame
```
## Step 4: Run your PiCar-X WebSocket Server
```bash
python3 ~/picar-x/example/picar_ws_server.py
```
---
