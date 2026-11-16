import argparse, os


def main():
    ap = argparse.ArgumentParser("memory-mesh")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve"); s.add_argument("--host", default="127.0.0.1"); s.add_argument("--port", type=int, default=8765)
    sub.add_parser("admin-key")
    a = ap.parse_args()
    from .config import Settings
    st = Settings().ensure()
    if a.cmd == "admin-key":
        print(st.admin_key); return
    import uvicorn
    from .api import create_app
    print(f"Memory Mesh API on http://{a.host}:{a.port}  (admin key file: {st.data_dir / 'admin.key'})")
    uvicorn.run(create_app(), host=a.host, port=a.port)
