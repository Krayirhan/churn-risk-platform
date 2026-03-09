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
    print("  Adım süreleri:")
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
        print("\n  Confusion Matrix:")
        print(f"    TN={cm.get('true_negative', '?')}  FP={cm.get('false_positive', '?')}")
        print(f"    FN={cm.get('false_negative', '?')}  TP={cm.get('true_positive', '?')}")
    print("=" * 60)


def cmd_monitor(args) -> None:
    """
    Model izleme raporu üretir.

    Tahmin loglarından drift analizi yapar ve performans durumunu kontrol eder.
    """
    from src.components.prediction_logger import PredictionLogger
    from src.components.drift_detector import DriftDetector
    from src.components.model_monitor import ModelMonitor

    logging.info("CLI → Monitoring kontrolü başlatılıyor...")

    # Tahmin istatistikleri
    pred_logger = PredictionLogger()
    stats = pred_logger.get_stats(days=args.days if hasattr(args, 'days') else 7)

    print("\n" + "=" * 60)
    print("📊 MONİTORİNG RAPORU")
    print("=" * 60)
    print(f"  Toplam tahmin  : {stats.get('total_predictions', 0)}")
    print(f"  Churn oranı    : %{stats.get('churn_rate', 0)}")
    print(f"  Ort. olasılık  : {stats.get('avg_churn_probability', 'N/A')}")
    print(f"  Risk dağılımı : {stats.get('risk_distribution', {})}")

    # Drift analizi
    features_df = pred_logger.get_features_df(n=500, days=7)
    if not features_df.empty:
        try:
            detector = DriftDetector()
            drift_report = detector.analyze(features_df)
            print(f"\n  Drift Durumu   : {drift_report.get('alert_level', 'unknown')}")
            print(f"  Drift Oranı    : %{drift_report.get('drift_ratio', 0)*100:.1f}")
            drifted = drift_report.get('drifted_features', [])
            if drifted:
                print(f"  Drift Feature  : {', '.join(drifted)}")
        except FileNotFoundError:
            print("\n  ⚠ Referans istatistikler bulunamadı (drift analizi atlandı)")
    else:
        print("\n  ℹ Drift analizi için yeterli tahmin logu yok")

    # Performans kontrolü
    import os
    if os.path.exists("artifacts/metrics.json"):
        from src.utils.common import load_json
        data = load_json("artifacts/metrics.json")
        monitor = ModelMonitor()
        perf = monitor.check_performance(data.get("metrics", {}))
        print(f"\n  Performans     : {perf.get('status', 'unknown')}")
        for m, comp in perf.get('comparisons', {}).items():
            icon = '✅' if not comp['degraded'] else '⚠'
            print(f"    {icon} {m}: {comp['baseline']:.4f} → {comp['current']:.4f} ({comp['drop_pct']:+.1f}%)")
    print("=" * 60)


def cmd_retrain(args) -> None:
    """
    Manuel retrain tetikler.
    """
    from src.pipeline.retrain_pipeline import RetrainPipeline

    logging.info("CLI → Retrain pipeline başlatılıyor...")
    pipeline = RetrainPipeline()
    force = hasattr(args, 'force') and args.force
    result = pipeline.run(reason="manual", force=force)

    print("\n" + "=" * 60)
    if result["retrained"]:
        print("🎯 YENİDEN EĞİTİM TAMAMLANDI")
        train_r = result.get("result", {})
        print(f"  Model  : {train_r.get('best_model', 'N/A')}")
        print(f"  F1     : {train_r.get('best_f1', 0):.4f}")
    else:
        print("⚠ Retrain YAPILMADI")
        print(f"  Neden  : {result.get('message', 'Bilinmiyor')}")
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
    print(f"   Docs: http://{host}:{port}/docs")
    print("   Durdurmak için Ctrl+C\n")

    uvicorn.run("app:app", host=host, port=port, reload=False)


def script_train() -> None:
    """
    pyproject.toml console-script girişi için argümansız train wrapper'ı.
    """
    args = argparse.Namespace()
    cmd_train(args)


def script_serve() -> None:
    """
    pyproject.toml console-script girişi için varsayılan serve wrapper'ı.
    """
    args = argparse.Namespace(host="127.0.0.1", port=8000)
    cmd_serve(args)


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
        "--monitor",
        action="store_true",
        help="Monitoring raporu üretir (drift + performans kontrolü)",
    )
    parser.add_argument(
        "--retrain",
        action="store_true",
        help="Modeli yeniden eğitir",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Retrain için cooldown ve diğer kontrolleri atla",
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
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Monitoring için kaç gün geriye bakılacak (varsayılan: 7)",
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
    if not any([args.train, args.predict, args.predict_inline, args.info,
                args.serve, args.monitor, args.retrain]):
        parser.print_help()
        sys.exit(0)

    # ─── Komut yönlendirmesi ───
    if args.train:
        cmd_train(args)

    if args.predict or args.predict_inline:
        cmd_predict(args)

    if args.info:
        cmd_info(args)

    if args.monitor:
        cmd_monitor(args)

    if args.retrain:
        cmd_retrain(args)

    if args.serve:
        cmd_serve(args)


if __name__ == "__main__":
    main()
