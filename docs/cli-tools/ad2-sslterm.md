# `ad2-sslterm`

**Purpose:**  
Secure SSL terminal session to an AlarmDecoder device using socket interface.

---

## 🔧 Usage

```bash
./bin/ad2-sslterm <host:port> <ca_cert> <client_cert> <client_key> [--debug]


## Examples

./bin/ad2-sslterm 192.168.1.10:10000 ca.crt client.crt client.key --debug
