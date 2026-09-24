import dns.resolver

r = dns.resolver.Resolver()
r.nameservers = ['8.8.8.8', '1.1.1.1']
try:
    answers = r.resolve('_mongodb._tcp.cluster0.lp41f.mongodb.net', 'SRV')
    print("SRV hosts found:")
    nodes = []
    for a in answers:
        host = str(a.target).rstrip(".")
        print(f"  {host}:{a.port}")
        nodes.append(f"{host}:{a.port}")
    
    txt = r.resolve('cluster0.lp41f.mongodb.net', 'TXT')
    for t in txt:
        print("TXT record:", t)
    
    print("\nDirect Standard MongoDB URI:")
    direct_uri = f"mongodb://skyvotes:skyhighvotes2027@{','.join(nodes)}/Nsesa?ssl=true&authSource=admin&replicaSet={str(txt[0]).strip('\"').split('=')[1]}"
    print(direct_uri)
except Exception as e:
    print("DNS lookup failed:", e)
