# Hosty

This is a restaurant table management application meant to assist a host / greeter in seating guests for a group of
servers / waiters.
It also provides basic reservation management.

## Features

- Table states (Clean, Sat, Dirty)
- Floorplan Saving
  - Tracks up to 5 previously loaded floorplans for quick access
  - Preview floorplans before loading them (only with the floorplan dialog)
- 2 Counting modes (table count or head count)
- Track server's total and active tables or head count
- Predict which server should be seated next
- Estimate how busy the kitchen is based on what you've sat recently (overflow)
  - Customize color coded thresholds (to indicate a color based on overflow)
  - Customize the kitchen's speed estimation (in case you've got a slow or fast kitchen)
- Manage reservations (create, edit, cancel, mark as arrived)
  - Fill in date, time, name, size, phone number and extra notes

The program is made with Python (version 3.9.7), utilizing the Qt framework for its rich library of GUI elements.
