Fleet Management App

A Django web app for managing a vehicle fleet in one place. It tracks each vehicle's details and condition, logs service history, and flags maintenance that is due or overdue, based on whichever comes first: date or mileage.

Built for a mixed fleet, including armored and special-purpose vehicles.

Features
Accounts: staff sign in with a temporary password and must change it on first login
User profiles: each user has a department and job title; departments are managed by an administrator, not hard-coded
Dashboard: landing page after login
Vehicles:
Vehicle records: fleet number, plate, VIN, make, model, year, type, odometer and status
Admin-editable vehicle types (sedan, pickup, armored, cash-in-transit, and so on)
Armored vehicle fields: armor rating and special equipment
Condition rating and notes for each vehicle
Registration and insurance expiry dates
Driver assignment
Service tracking:
Admin-editable service types with repeat intervals by days and/or distance
Service history: who did the work, when, at what odometer, and the cost
Next-due date and odometer filled in automatically from the service type
Status for each vehicle: up to date, due soon, overdue, or no service history
Damage and inspection history: planned as a separate app
Project structure
src/
├── accounts/    # authentication, forced password change, user profiles
├── core/        # dashboard
├── vehicles/    # vehicles, service types, service records, placeholder drivers
└── manage.py
Tech stack
Python
Django
HTML templates
Hosted on PythonAnywhere
Getting started
bash
# Clone the repository
git clone <repo-url>
cd fleet/src

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up the database
python manage.py makemigrations
python manage.py migrate

# Create an admin account
python manage.py createsuperuser

# Run the development server
python manage.py runserver

Then open http://127.0.0.1:8000/ and sign in.

First-time setup

After creating your superuser, sign in to the Django admin at /admin/ and add:

Departments for your organization
Vehicle types (for example Sedan, Pickup, Armored Vehicle)
Service types with repeat intervals (for example Oil Change: 90 days / 5000 km)
Vehicles, then log their service history
Configuration

Optional settings in settings.py:

Setting	Default	Meaning
FLEET_DUE_SOON_DAYS	30	Days before a due date that a service shows as "due soon"
FLEET_DUE_SOON_DISTANCE	500	Distance before a due odometer reading that a service shows as "due soon"

Odometer readings use a single unit (km or miles) across the whole fleet. Pick one and stay consistent.

Roadmap
 Driver app, to replace the placeholder Driver model in vehicles
 Damage and inspection app, with a clickable vehicle body map
 Service due reminders and a dashboard summary
 Reports and exports
Notes

The Driver model in the vehicles app is a placeholder. When the driver app is built, the Vehicle.assigned_driver field will point to it, existing data will be migrated, and the placeholder will be removed.
