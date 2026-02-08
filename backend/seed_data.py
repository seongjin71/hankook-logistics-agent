"""
마스터 데이터 시딩 스크립트
- Products 50개, Customers 30개, Warehouses 3개, Vehicles 15대, Inventory 150개 레코드
- 실행: cd backend && python seed_data.py
"""

import random
import sys
import os

# backend/ 디렉토리 기준으로 app 패키지를 찾을 수 있도록 경로 설정
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal, Base
from app.models import Product, Customer, Warehouse, Vehicle, Inventory
from app.models.product import ProductCategory, PriorityGrade
from app.models.customer import CustomerGrade
from app.models.vehicle import VehicleType, VehicleStatus


def seed_products(session):
    """50개 타이어 SKU 생성 — 한국타이어 실제 브랜드명 활용"""
    products = []
    idx = 0

    # Ventus 시리즈 (승용, 고성능) — 15개, Grade A/B
    ventus_models = [
        ("Ventus Prime 4", "205/55R16", 8.5),
        ("Ventus Prime 4", "195/65R15", 8.0),
        ("Ventus Prime 4", "225/45R17", 9.0),
        ("Ventus Prime 4", "215/55R17", 9.2),
        ("Ventus Prime 4", "225/50R17", 9.5),
        ("Ventus S1 evo3", "245/40R18", 9.8),
        ("Ventus S1 evo3", "255/35R19", 10.2),
        ("Ventus S1 evo3", "225/40R18", 9.3),
        ("Ventus S1 evo3", "235/40R19", 10.0),
        ("Ventus S1 evo3", "245/45R18", 10.5),
        ("Ventus V12 evo2", "205/50R17", 8.8),
        ("Ventus V12 evo2", "225/45R18", 9.5),
        ("Ventus V12 evo2", "245/40R17", 9.7),
        ("Ventus iON S", "255/45R20", 12.0),
        ("Ventus iON S", "235/55R19", 11.5),
    ]
    for name, size, weight in ventus_models:
        idx += 1
        grade = PriorityGrade.A if idx <= 8 else PriorityGrade.B
        sku = f"HK-P-{size.replace('/', '-')}-{idx:03d}"
        products.append(Product(
            sku_code=sku,
            name=f"{name} {size}",
            category=ProductCategory.PASSENGER,
            tire_size=size,
            weight_kg=weight,
            priority_grade=grade,
        ))

    # Kinergy 시리즈 (승용, 사계절) — 10개, Grade B
    kinergy_models = [
        ("Kinergy 4S2", "205/55R16", 8.3),
        ("Kinergy 4S2", "195/65R15", 7.8),
        ("Kinergy 4S2", "225/45R17", 9.0),
        ("Kinergy 4S2", "215/60R16", 8.7),
        ("Kinergy 4S2", "205/60R16", 8.4),
        ("Kinergy Eco2", "185/65R15", 7.2),
        ("Kinergy Eco2", "195/55R16", 7.5),
        ("Kinergy Eco2", "175/65R14", 6.8),
        ("Kinergy GT", "205/55R16", 8.2),
        ("Kinergy GT", "215/55R17", 8.9),
    ]
    for name, size, weight in kinergy_models:
        idx += 1
        sku = f"HK-P-{size.replace('/', '-')}-{idx:03d}"
        products.append(Product(
            sku_code=sku,
            name=f"{name} {size}",
            category=ProductCategory.PASSENGER,
            tire_size=size,
            weight_kg=weight,
            priority_grade=PriorityGrade.B,
        ))

    # Dynapro 시리즈 (SUV) — 10개, Grade A/B
    dynapro_models = [
        ("Dynapro HP2", "235/60R18", 12.5),
        ("Dynapro HP2", "225/65R17", 11.8),
        ("Dynapro HP2", "255/55R18", 13.0),
        ("Dynapro HP2", "245/60R18", 12.8),
        ("Dynapro HP2", "265/50R20", 14.5),
        ("Dynapro AT2", "265/70R16", 14.0),
        ("Dynapro AT2", "245/70R16", 13.2),
        ("Dynapro AT2", "265/65R17", 13.8),
        ("Dynapro HT", "225/70R16", 12.0),
        ("Dynapro HT", "235/75R15", 11.5),
    ]
    for name, size, weight in dynapro_models:
        idx += 1
        grade = PriorityGrade.A if idx <= 30 else PriorityGrade.B
        sku = f"HK-S-{size.replace('/', '-')}-{idx:03d}"
        products.append(Product(
            sku_code=sku,
            name=f"{name} {size}",
            category=ProductCategory.SUV,
            tire_size=size,
            weight_kg=weight,
            priority_grade=grade,
        ))

    # SmartFlex 시리즈 (트럭/버스) — 10개, Grade B/C
    smartflex_models = [
        ("SmartFlex AH35", "295/80R22.5", 55.0),
        ("SmartFlex AH35", "315/80R22.5", 60.0),
        ("SmartFlex DH35", "295/80R22.5", 56.0),
        ("SmartFlex DH35", "315/70R22.5", 58.0),
        ("SmartFlex TH31", "385/65R22.5", 62.0),
        ("e-CUBE MAX DL21", "295/80R22.5", 54.0),
        ("e-CUBE MAX DL21", "315/80R22.5", 59.0),
        ("SmartWork AM15+", "12R22.5", 52.0),
        ("SmartWork DM09", "295/80R22.5", 55.5),
        ("SmartWork TM15+", "385/65R22.5", 61.0),
    ]
    for i, (name, size, weight) in enumerate(smartflex_models):
        idx += 1
        grade = PriorityGrade.B if i < 5 else PriorityGrade.C
        cat = ProductCategory.TRUCK if i < 7 else ProductCategory.BUS
        sku = f"HK-T-{size.replace('/', '-').replace('.', '')}-{idx:03d}"
        products.append(Product(
            sku_code=sku,
            name=f"{name} {size}",
            category=cat,
            tire_size=size,
            weight_kg=weight,
            priority_grade=grade,
        ))

    # Vantra 시리즈 (밴/경상용) — 5개, Grade C
    vantra_models = [
        ("Vantra LT", "195/75R16C", 10.5),
        ("Vantra LT", "205/75R16C", 11.0),
        ("Vantra LT", "215/75R16C", 11.5),
        ("Vantra ST AS2", "195/70R15C", 9.8),
        ("Vantra ST AS2", "205/65R16C", 10.2),
    ]
    for name, size, weight in vantra_models:
        idx += 1
        sku = f"HK-V-{size.replace('/', '-').replace('.', '')}-{idx:03d}"
        products.append(Product(
            sku_code=sku,
            name=f"{name} {size}",
            category=ProductCategory.TRUCK,
            tire_size=size,
            weight_kg=weight,
            priority_grade=PriorityGrade.C,
        ))

    session.add_all(products)
    session.commit()
    print(f"  [OK] Products: {len(products)}개 생성")
    return products


def seed_customers(session):
    """30개 고객사 생성"""
    customers = []
    regions = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
               "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주"]

    # VIP 5개 — OEM 완성차 업체
    vip_list = [
        ("현대자동차", "서울"),
        ("기아자동차", "서울"),
        ("르노코리아", "부산"),
        ("KG모빌리티", "경기"),
        ("한국GM", "인천"),
    ]
    for i, (name, region) in enumerate(vip_list, 1):
        customers.append(Customer(
            name=name,
            customer_code=f"VIP-{i:03d}",
            region=region,
            grade=CustomerGrade.VIP,
            sla_hours=12,
        ))

    # STANDARD 15개 — 대형 타이어 대리점/체인
    standard_list = [
        ("타이어뱅크 강남점", "서울"),
        ("타이어뱅크 부산점", "부산"),
        ("타이어뱅크 대구점", "대구"),
        ("타이어뱅크 대전점", "대전"),
        ("타이어뱅크 광주점", "광주"),
        ("타이어프로 서초점", "서울"),
        ("타이어프로 해운대점", "부산"),
        ("타이어프로 수원점", "경기"),
        ("오토피아 강서점", "서울"),
        ("오토피아 인천점", "인천"),
        ("티스테이션 잠실점", "서울"),
        ("티스테이션 분당점", "경기"),
        ("피렐리코리아", "서울"),
        ("한국타이어 직영 울산", "울산"),
        ("한국타이어 직영 창원", "경남"),
    ]
    for i, (name, region) in enumerate(standard_list, 1):
        customers.append(Customer(
            name=name,
            customer_code=f"STD-{i:03d}",
            region=region,
            grade=CustomerGrade.STANDARD,
            sla_hours=24,
        ))

    # ECONOMY 10개 — 소형 정비소, 온라인 판매처
    economy_list = [
        ("김사장 타이어", "충남"),
        ("대림 정비소", "전북"),
        ("동해 타이어센터", "강원"),
        ("남해 카센터", "경남"),
        ("제주오토", "제주"),
        ("카닥 온라인몰", "서울"),
        ("타이어온 쇼핑몰", "경기"),
        ("차량나라 정비", "충북"),
        ("용인 타이어샵", "경기"),
        ("춘천 카센터", "강원"),
    ]
    for i, (name, region) in enumerate(economy_list, 1):
        customers.append(Customer(
            name=name,
            customer_code=f"ECO-{i:03d}",
            region=region,
            grade=CustomerGrade.ECONOMY,
            sla_hours=48,
        ))

    session.add_all(customers)
    session.commit()
    print(f"  [OK] Customers: {len(customers)}개 생성")
    return customers


def seed_warehouses(session):
    """3개 출하 창고 생성"""
    warehouses = [
        Warehouse(
            code="WH-DKJ",
            name="대전공장 물류센터",
            location_lat=36.35,
            location_lng=127.38,
            dock_count=8,
        ),
        Warehouse(
            code="WH-GMS",
            name="금산 물류센터",
            location_lat=36.10,
            location_lng=127.49,
            dock_count=6,
        ),
        Warehouse(
            code="WH-PYT",
            name="평택항 물류센터",
            location_lat=36.97,
            location_lng=126.83,
            dock_count=10,
        ),
    ]
    session.add_all(warehouses)
    session.commit()
    print(f"  [OK] Warehouses: {len(warehouses)}개 생성")
    return warehouses


def seed_vehicles(session, warehouses):
    """15대 배송 차량 생성 — 각 창고에 5대씩 배정"""
    vehicles = []
    vid = 0

    for wh in warehouses:
        # 5T 2대, 11T 2대, 25T 1대 = 5대/창고
        specs = [
            (VehicleType.T5, 5000.0),
            (VehicleType.T5, 5000.0),
            (VehicleType.T11, 11000.0),
            (VehicleType.T11, 11000.0),
            (VehicleType.T25, 25000.0),
        ]
        for vtype, capacity in specs:
            vid += 1
            vehicles.append(Vehicle(
                vehicle_code=f"VH-{vid:03d}",
                vehicle_type=vtype,
                max_capacity_kg=capacity,
                status=VehicleStatus.AVAILABLE,
                current_lat=wh.location_lat,
                current_lng=wh.location_lng,
                current_speed_kmh=0,
                fuel_level_pct=100.0,
                warehouse_id=wh.id,
            ))

    session.add_all(vehicles)
    session.commit()
    print(f"  [OK] Vehicles: {len(vehicles)}대 생성")
    return vehicles


def seed_inventory(session, warehouses, products):
    """각 창고 × 각 SKU = 150개 재고 레코드 생성"""
    inventories = []
    for wh in warehouses:
        for prod in products:
            # Grade A 제품은 재고를 더 많이 보유
            if prod.priority_grade == PriorityGrade.A:
                available = random.randint(200, 500)
            else:
                available = random.randint(100, 500)

            safety = random.randint(50, 100)

            inventories.append(Inventory(
                warehouse_id=wh.id,
                product_id=prod.id,
                available_qty=available,
                reserved_qty=0,
                safety_stock=safety,
            ))

    session.add_all(inventories)
    session.commit()
    print(f"  [OK] Inventory: {len(inventories)}개 레코드 생성")
    return inventories


def main():
    print("=" * 60)
    print("한국타이어 출하물류 시스템 — 마스터 데이터 시딩")
    print("=" * 60)

    # 테이블 전체 재생성
    print("\n[1/6] 테이블 생성 중...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("  [OK] 테이블 생성 완료")

    session = SessionLocal()
    try:
        print("\n[2/6] Products 시딩...")
        products = seed_products(session)

        print("\n[3/6] Customers 시딩...")
        customers = seed_customers(session)

        print("\n[4/6] Warehouses 시딩...")
        warehouses = seed_warehouses(session)

        print("\n[5/6] Vehicles 시딩...")
        vehicles = seed_vehicles(session, warehouses)

        print("\n[6/6] Inventory 시딩...")
        inventory = seed_inventory(session, warehouses, products)

        print("\n" + "=" * 60)
        print("시딩 완료!")
        print(f"  Products:   {len(products)}개")
        print(f"  Customers:  {len(customers)}개")
        print(f"  Warehouses: {len(warehouses)}개")
        print(f"  Vehicles:   {len(vehicles)}대")
        print(f"  Inventory:  {len(inventory)}개 레코드")
        print("=" * 60)

    except Exception as e:
        session.rollback()
        print(f"\n[ERROR] 시딩 실패: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
