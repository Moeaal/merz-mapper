# udev rules

One file per device, so a stable name does not depend on the order the USB devices were found.
```bash
sudo cp 99-merz-*.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
ls -l /dev/rplidar /dev/c920
```
The vendor and product IDs are the expected values for these models, not read from the real devices yet.
Check each one when the parts arrive.
