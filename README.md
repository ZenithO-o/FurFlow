# FurFlow
software for LoRa based room status sensors


### Config setup

The config file has a couple of sections that can be modified to suit your needs.

- `TimeZone`: The timezone that is being used for displaying telegram messages.

- `DateString`: The formatting of time based inputs.

- `Devices`: The map of devices on the network.
    - `location`: Each device must have a location associated with it.

- `Locations`: The map of locations and their related features.
    - `alias`: The display name of a location.
    - `capacity`: The number of devices that can be at a location. Used for the `capacity` output.

- `Serial`: Config for listening to serial. Uses the kwargs of [serial.Serial](https://pyserial.readthedocs.io/en/latest/pyserial_api.html)

- `SensorReadouts`: The list of variables that the devices on the networks output.

- `Output`: The list of variables to be outputted out onto Telegram.

- `Readouts`: The map of variables that are supported.
    - `alias`: The displayed name of the variable.
    - `ending`: If the variable has a unit, this is placed after the value.
    - `precision`: the number of decimals to round a variable with.

### .env setup

The `.env` file contains either secrets or persistent data that should not be stored in the config. This is the layout of the `.env` file:

```
TELEGRAM_KEY=[PUT_KEY_HERE]
CHAT_ID=[PUT_ID_HERE]
```
