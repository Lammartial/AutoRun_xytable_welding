# SAP DSP (DiSi) Service connector
Provides the REST interface to the MES system, more concrete the DSP.


# Mockup Server
To bypass the need of SAP we have this handy mockup server tool based on FastAPI web server.

Mockup server port is 8000 by default. It is selectable by the .CMD batch file so you can easily configure more than one server to run in parallel on this PC by adding a `--port` parameter on the call:

## Example:
   uvicorn mockup.server:app --host 0.0.0.0 --port 8011
   uvicorn mockup.server:app --host 0.0.0.0 --port 8022
   uvicorn mockup.server:app --host 0.0.0.0 --port 8033

Note: Please not that there is no --reload parameter so you can change the CONFIGURED_PRODUCT before calling each mockup -> on TSDEV we can run 3 mockups for the lines that way!

Besides that  you need also to set this port in the station_config.yaml of a workstation under test or used for rework on a line.

There are prepared windows batch files to start separate servers.

## Configuration

To select a product for the mockup, edit only mockup/config.py file.
Information about the product need to be edited in mockup/information.py file.


MR_2023, MR_2025
