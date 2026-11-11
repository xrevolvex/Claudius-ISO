# Running Claudius in Oracle VirtualBox

These steps use VirtualBox 7.x. Older versions have the same settings in slightly different places.

## 1. Create the VM

**Machine → New**

| Setting | Value |
|---|---|
| Name | Claudius |
| ISO Image | `claudius-1.0-amd64.iso` |
| Type / Version | Linux / **Debian (64-bit)** |
| Skip Unattended Installation | **tick it** (Claudius has its own installer) |

Click **Next**.

| Hardware | Recommended (fast) | Minimum |
|---|---|---|
| Base Memory | **8192 MB** | 2048 MB |
| Processors | **4** (or half your real cores) | 1 |
| Enable EFI | optional (both work) | |
| Hard disk | **25 GB**, VDI, dynamically allocated | 15 GB |

Click **Finish**.

## 2. Tune the VM for speed

Select the VM → **Settings**:

- **System → Processor:** tick **Enable PAE/NX**
- **System → Acceleration:** Paravirtualization **KVM**, keep **Nested Paging** on
- **Display → Screen:** Graphics Controller **VMSVGA**, Video Memory **128 MB**, *3D acceleration off* (it is slower for this kind of guest)
- **Storage:** controller **SATA (AHCI)**, and tick **Use Host I/O Cache** on the controller. On the disk itself tick **Solid-state Drive** if your PC has an SSD
- **Audio:** Host Audio Driver *Default*, Controller *Intel HD Audio*
- **Network:** Adapter 1 **NAT** (internet works out of the box)
- **USB:** USB 2.0 or 3.0 controller

On Windows, also make sure **Hyper-V / Windows Hypervisor Platform** is turned off if VirtualBox shows a "turtle" icon in the status bar, because that means it's running in slow mode.

## 3. Boot

Start the VM. The Claudius boot menu appears and starts by itself after 5 seconds:

- **Start Claudius (amd64)**: the normal live session.
- **Start Claudius in RAM (fastest, needs 4 GB+)**: copies the whole system into memory first (about 20 to 40 seconds longer to boot). After that everything runs from RAM. **Pick this on an 8 GB VM.**
- **fail-safe mode**: if graphics don't work.

At the login screen, type the password **`claudius`** (user `claudius`).

## 4. Install to the virtual disk (optional)

Double-click **Install Claudius** on the desktop, or use the **Install Claudius** button in the Welcome window. Follow the steps (language, time zone, keyboard, *Erase disk*, your name and password). When it finishes, shut down, remove the ISO under **Settings → Storage**, and start the VM again.

An installed Claudius keeps your files and apps and boots faster than the live ISO.

## 5. Screen size, clipboard and shared folders

Claudius starts at a comfortable resolution automatically. To change it: **Menu → Settings → Display**.

For **automatic resizing with the window**, **shared clipboard** and **shared folders**, install the VirtualBox Guest Additions on an installed Claudius:

```bash
claudius install build-essential linux-headers-amd64
# VirtualBox menu: Devices → Insert Guest Additions CD image
sudo sh /media/cdrom0/VBoxLinuxAdditions.run   # or the path shown in the file manager
sudo reboot
```

## Troubleshooting

| Problem | Fix |
|---|---|
| Black screen after the boot menu | Settings → Display → set **VMSVGA** and 128 MB, or boot the *fail-safe* entry |
| Very slow, turtle icon in VirtualBox | Turn off Hyper-V / Windows Hypervisor Platform / Memory Integrity in Windows, then reboot Windows |
| "Kernel requires an x86-64 CPU" | Version must be *Debian (64-bit)*. Enable VT-x/AMD-V in your PC's BIOS |
| No internet | Settings → Network → Adapter 1 → NAT, cable connected ticked |
| Wrong keyboard layout | Menu → Settings → Keyboard → Layout, untick *Use system defaults* and add yours |
| Want to see the active profile | Open a terminal and type `claudius ram` |
