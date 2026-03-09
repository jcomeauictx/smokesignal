# smokesignal
An idea for permissionless data communications

Two laptops facing each other, cameras on. One flashes a QR code to the
other. If the other sees it, it flashes the same code back, or it flashes
a code of its own data plus a hash of the data it saw.

A community of laptops in windows could have a mesh of these, with houses
with more than one computer serving as routers.

Scaling wider, telescopes and large screens could potentially enable
point-to-point links many kilometers distant, linking community meshes.

## quickstart

install on a digitalocean droplet

1. create a droplet in your nearest data center: Debian 13, Basic, Regular, $4/month in March 2026, which gets you 512MB RAM, 10GB SSD, and 500GB transfer. add the IP to your /etc/hosts as: `echo 10.23.221.67 droplet | sudo tee -a /etc/hosts`. or advanced users can add to $HOME/.ssh/config without sudo access. make sure to enable, or add, your ssh key(s) to the droplet on creation.
2. `make droplet`

## future directions

* add routing within the mesh and over the Internet, for those nodes with access. think of GPS schemes like [Tony Hain's draft spec](https://datatracker.ietf.org/doc/html/draft-hain-ipv6-geo-addr-02) and [Imielinski's similar proposal](https://www.rfc-editor.org/rfc/rfc2009.html). also see my [w-a-s-t-e project](https://github.com/jcomeauictx/w-a-s-t-e).
* precede each upload with a form-generated JSON packet that specifies requested treatment for the upload, things like "ipfs", "email-to", "allow-download", etc., and the node owner can enable or disable these requests as he sees fit. the return json packet should let the user know the status of his request, either accepted or denied, and if ipfs or allow-download, should return the identifier for future retrieval.

## developer's notes
* once prototype is working, move to javascript frontend and keep python
  running under uwsgi on backend. then it can run on iPhone with iSH. (done)
* needs my fork of zbar for returning bytes from decode with Python-tkinter
  version, and my forks of qrcodejs and jsQR for the browser-based version.
