# State model for the iot raspi state cover device

## Pins

There are three gpio pins involved

* pin_down: For the lower magnetic contact. If closed, then the cover is closed.
* pin_up: For the upper magnetic contact. If closed, then the cover is open.
* trigger_pin: Controls the cover by giving short signals to the garage door controller.

## States

The following internal states are possible

* open
* opening
* closed
* closing
* stopped_opening: report as unknown
* stopped_closing: report as unknown

See also https://www.home-assistant.io/integrations/cover.mqtt/ which has fewer states but they are not sufficienct.

## Commands

The following commands can arrive from MQTT

* OPEN
* CLOSE
* STOP

## When a MQTT command arrives

| command| previous state | action    | new state      |
|--------|----------------|-----------|----------------|
| OPEN   | open           |           |                |
|        | opening        |           |                |
|        | closed         | trigger   |                |
|        | closing        | 2x trigger| opening        |
|        | stopped_opening| 2x trigger| opening        |
|        | stopped_closing| trigger   | opening        |
|        | unknwon        | trigger * |                |
| CLOSE  | open           | trigger   |                |
|        | opening        | 2x trigger| closing        |
|        | closed         |           |                |
|        | closing        |           |                |
|        | stopped_opening| trigger   | closing        |
|        | stopped_closing| 2x trigger| closing        |                                  
|        | unknwon        | trigger * |                |
| STOP   | open           |           |                |
|        | opening        | trigger   | stopped_opening|
|        | closed         |           |                |
|        | closing        | trigger   | stopped_closing|
|        | stopped_opening|           |                |
|        | stopped_closing|           |                |
|        | unknown        |           |                |

In most cases the new state is not set based on the command. Instead the immediately following GPIO pin changes will cause the correct state chences, see next table. Only when the following states can not be observed immediately the new status is defined here.

When coming from 'unknown' state: trigger * once to cause a state change. This will lead to a well-defined state and then the commands and tracking of changes works properly.

## When one of the input pins changes


| pin change              | previous state  | action | new state |
|-------------------------|-----------------|--------|-----------|
| pin_down open -> closed | open            |        | closed *  |
|                         | opening         |        | closed *  |
|                         | closed          |        | closed *  |
|                         | closing         |        | closed    |
|                         | stopped_opening |        | closed *  |
|                         | stopped_closing |        | closed *  |
| pin_down closed -> open | open            |        | opening * |
|                         | opening         |        | opening * |
|                         | closed          |        | opening   |
|                         | closing         |        | opening * |
|                         | stopped_opening |        | opening * |
|                         | stopped_closing |        | opening * |
| pin_up open -> closed   | open            |        | open *    |
|                         | opening         |        | open      |
|                         | closed          |        | open *    |
|                         | closing         |        | open *    |
|                         | stopped_opening |        | open *    |
|                         | stopped_closing |        | open *    |
| pin_up closed -> open   | open            |        | closing   |
|                         | opening         |        | closing * |
|                         | closed          |        | closing * |
|                         | closing         |        | closing * |
|                         | stopped_opening |        | closing * |
|                         | stopped_closing |        | closing * |

When new state has a '*' then it arrived there with irregularities because other states should have been inbetween. It still adopts the new state because 'pin_down' and 'pin_up' are the primary sensors for the state of the cover. 

If 'pin_down' and 'pin_up' are closed simultaneously, then something is seriously wrong!


