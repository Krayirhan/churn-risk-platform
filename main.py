# ============================================================================
# main.py — Projenin CLI Giriş Noktası (Entry Point)
# ============================================================================
# NEDEN BU DOSYA VAR?
#   Komut satırından projeyi çalıştırmak için tek giriş noktası.
#   Eğitim, tahmin ve bilgi alma komutlarını argparse ile yönetir.
#
# KULLANIM:
#   python main.py --train                         # Tam eğitim pipeline
#   python main.py --predict --input sample.json   # JSON dosyasından tahmin
#   python main.py --predict-inline '{...}'        # Inline JSON ile tahmin
#   python main.py --info                          # Model bilgisi göster
#   python main.py --serve                         # FastAPI sunucusunu başlat
#
# NEDEN ARGPARSE?
#   - Python stdlib'de yerleşik → ek bağımlılık yok
#   - --help ile otomatik yardım menüsü oluşturur
#   - Production ortamında CLI aracı olarak kullanılabilir
# ============================================================================

import sys
import json
import argparse

from src.logger import logging


def cmd_train(args) -> None:
    """
    Eğitim pipeline'ını çalıştırır.

    Ingestion → Transformation → Training → Evaluation zincirini
    sırasıyla çalıştırır ve sonucu konsola yazdırır.
    """
    from src.pipeline.train_pipeline import TrainPipeline

    logging.info("CLI → Eğitim pipeline başlatılıyor...")
    pipeline = TrainPipeline()
    result = pipeline.run()

    # Konsola güzel özet yazdır
    print("\n" + "=" * 60)
    print("🎯 EĞİTİM TAMAMLANDI")
    print("=" * 60)
    print(f"  Mod          : {result['mode'].upper()}")
    print(f"  En iyi model : {result['best_model']}")
    print(f"  Best F1      : {result['best_f1']:.4f}")
    print(f"  Toplam süre  : {result['total_time']}s")
    print(f"  Adım süreleri:")
    for step, t in result["timings"].items():
        if step != "total":
            print(f"    {step:20s} : {t}s")
    print("=" * 60)


def cmd_predict(args) -> None:
    """
    Tekil müşteri tahmini yapar.

    İki yol desteklenir:
      1. --input sample.json  → JSON dosyasından okur
      2. --predict-inline '{"tenure": 24, ...}'  → Komut satırından inline JSON
    """
    from src.pipeline.predict_pipeline import PredictPipeline

    # ─── Girdiyi belirle ───
    if args.input:
        # JSON dosyasından oku
        with open(args.input, "r", encoding="utf-8") as f:
            customer_data = json.load(f)
        logging.info(f"CLI → JSON dosyasından tahmin: {args.input}")
    elif args.predict_inline:
        # Inline JSON
        customer_data = json.loads(args.predict_inline)
        logging.info("CLI → Inline JSON ile tahmin")
    else:
        # Varsayılan örnek müşteri (demo amaçlı)
        customer_data = {
            "tenure": 2,
            "MonthlyCharges": 89.10,
            "TotalCharges": 178.20,
            "Contract": "Month-to-month",
            "InternetService": "Fiber optic",
            "OnlineSecurity": "No",
            "TechSupport": "No",
            "PaymentMethod": "Electronic check",
            "PaperlessBilling": "Yes",
        }
        logging.info("CLI → Varsayılan örnek müşteri ile tahmin")

    # ─── Toplu veya tekil tahmin ───
    pipeline = PredictPipeline()

    if isinstance(customer_data, list):
        # Toplu tahmin (JSON dosyasında liste varsa)
        results = pipeline.predict_batch(customer_data)
        print("\n" + "=" * 60)
        print(f"🔮 TOPLU TAHMİN SONUÇLARI ({len(results)} müşteri)")
        print("=" * 60)
        for r in results:
            status = "🔴 CHURN" if r["prediction"] == 1 else "🟢 KALACAK"
            print(
                f"  {r['customerID']:>15s}  {status}  "
                f"P={r['churn_probability']:.2%}  Risk={r['risk_level']}"
            )
        churn_n = sum(1 for r in results if r["prediction"] == 1)
        print(f"\n  Özet: {churn_n}/{len(results)} churn riski")
        print("=" * 60)
    else:
        # Tekil tahmin
        result = pipeline.predict(customer_data)
        status = "🔴 CHURN" if result["prediction"] == 1 else "🟢 KALACAK"
        print("\n" + "=" * 60)
        print("🔮 TAHMİN SONUCU")
        print("=" * 60)
        print(f"  Müşteri       : {result['customerID']}")
        print(f"  Tahmin        : {status}")
        print(f"  Olasılık      : {result['churn_probability']:.2%}")
        print(f"  Risk Seviyesi : {result['risk_level']}")
        print("=" * 60)


def cmd_info(args) -> None:
    """
    Eğitilmiş modelin bilgilerini gösterir.

    artifacts/metrics.json dosyasından metrikleri okuyup konsola yazdırır.
    Eğitim yapılmamışsa uyarı verir.
    """
    import os
    from src.utils.common import load_json

    metrics_path = "artifacts/metrics.json"
    if not os.path.exists(metrics_path):
        print("⚠ Henüz eğitilmiş model bulunamadı.")
        print("  Önce çalıştırın: python main.py --train")
        return

    metrics = load_json(metrics_path)
    print("\n" + "=" * 60)
    print("📊 MODEL BİLGİSİ")
    print("=" * 60)
    print(f"  Model     : {metrics.get('model_name', 'N/A')}")
    m = metrics.get("metrics", {})
    print(f"  Accuracy  : {m.get('accuracy', 'N/A')}")
    print(f"  F1-Score  : {m.get('f1', 'N/A')}")
    print(f"  Recall    : {m.get('recall', 'N/A')}")
    print(f"  Precision : {m.get('precision', 'N/A')}")
    print(f"  ROC-AUC   : {m.get('roc_auc', 'N/A')}")
    print(f"  PR-AUC    : {m.get('pr_auc', 'N/A')}")

    cm = metrics.get("confusion_matrix", {})
    if cm:
        print(f"\n  Confusion Matrix:")
        print(f"    TN={cm.get('true_negative', '?')}  FP={cm.get('false_positive', '?')}")
        print(f"    FN={cm.get('false_negative', '?')}  TP={cm.get('true_positive', '?')}")
    print("=" * 60)


def cmd_serve(args) -> None:
    """
    FastAPI sunucusunu başlatır.

    Varsayılan olarak localhost:8000'de çalışır.
    --host ve --port argümanları ile değiştirilebilir.
    """
    import uvicorn

    host = args.host if hasattr(args, "host") and args.host else "127.0.0.1"
    port = args.port if hasattr(args, "port") and args.port else 8000

    print(f"\n🚀 FastAPI sunucusu başlatılıyor → http://{host}:{port}")
    print("   Docs: http://{host}:{port}/docs")
    print("   Durdurmak için Ctrl+C\n")

    uvicorn.run("app:app", host=host, port=port, reload=False)


def build_parser() -> argparse.ArgumentParser:
    """
    Argparse parser'ını oluşturur.

    Desteklenen komutlar:
      --train          : Eğitim pipeline'ını çalıştır
      --predict        : Tahmin yap (--input ile JSON dosyası)
      --predict-inline : Inline JSON ile tahmin yap
      --info           : Model bilgilerini göster
      --serve          : FastAPI sunucusunu başlat
    """
    parser = argparse.ArgumentParser(
        prog="churn-risk-platform",
        description="Telco Customer Churn Risk Platform — CLI Aracı",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  python main.py --train
  python main.py --predict --input data/sample_customer.json
  python main.py --predict-inline '{"tenure":2,"MonthlyCharges":89.10}'
  python main.py --info
  python main.py --serve
  python main.py --serve --host 0.0.0.0 --port 9000
        """,
    )

    # ─── Ana komutlar (mutually exclusive değil — ayrı flagler) ───
    parser.add_argument(
        "--train",
        action="store_true",
        help="Tam eğitim pipeline'ını çalıştırır (Ingestion → Train → Eval)",
    )
    parser.add_argument(
        "--predict",
        action="store_true",
        help="Tekil/toplu müşteri tahmini yapar (--input ile)",
    )
    parser.add_argument(
        "--predict-inline",
        type=str,
        default=None,
        metavar="JSON",
        help="Inline JSON string ile tekil tahmin yapar",
    )
    parser.add_argument(
        "--input",
        type=str,
        default=None,
        metavar="FILE",
        help="Tahmin için JSON dosya yolu (--predict ile birlikte kullanılır)",
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Eğitilmiş modelin metriklerini gösterir",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="FastAPI REST API sunucusunu başlatır",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="API sunucu host adresi (varsayılan: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="API sunucu port numarası (varsayılan: 8000)",
    )

    return parser


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    """
    CLI argümanlarını parse edip ilgili komutu çalıştırır.
    Hiçbir argüman verilmezse yardım menüsünü gösterir.
    """
    parser = build_parser()
    args = parser.parse_args()

    # Hiçbir komut verilmemişse yardım göster
    if not any([args.train, args.predict, args.predict_inline, args.info, args.serve]):
        parser.print_help()
        sys.exit(0)

    # ─── Komut yönlendirmesi ───
    if args.train:
        cmd_train(args)

    if args.predict or args.predict_inline:
        cmd_predict(args)

    if args.info:
        cmd_info(args)

    if args.serve:
        cmd_serve(args)


if __name__ == "__main__":
    main()
