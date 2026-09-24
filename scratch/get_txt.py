import dns.resolver

r = dns.resolver.Resolver()
r.nameservers = ['8.8.8.8', '8.8.4.4', '1.1.1.1']
r.timeout = 10.0
r.lifetime = 15.0

try:
    txt = r.resolve('cluster0.lp41f.mongodb.net', 'TXT')
    for t in txt:
        print("TXT record:", t.to_text())
except Exception as e:
    print("TXT lookup failed:", e)

try:
    srv = r.resolve('_mongodb._tcp.cluster0.lp41f.mongodb.net', 'SRV')
    for s in srv:
        print("SRV record:", s.target, s.port)
except Exception as e:
    print("SRV lookup failed:", e)
