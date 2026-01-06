import pandas as pd
import csv
from django.shortcuts import render, redirect
from .forms import CombinedUploadForm
from django.db.models import Sum, F, Q
from django.core.paginator import Paginator
from django.db import transaction
from .models import VehicleRecord
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.views.decorators.clickjacking import xframe_options_sameorigin
from statistic.services import sync_sheet
from statistic.models import ActiveTrucksFinalGross

@login_required
def ifta_list(request):
    search = request.GET.get("search", "").strip()
    file_filter = request.GET.get("file_name", "all")  # uzimamo parametar sa URL-a

    records = VehicleRecord.objects.all()

    if search:
        records = records.filter(
            Q(vehicle__icontains=search) |
            Q(jurisdiction__icontains=search)
        )

    if file_filter != "all":
        records = records.filter(file_name=file_filter)

    records = records.order_by("vehicle", "jurisdiction")

    # --- agregirane vrednosti ---
    totals = records.aggregate(
        total_miles_sum=Sum('total_miles'),
        total_fuel_sum=Sum('fuel_qty')
    )

    paginator = Paginator(records, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    total_count = records.count()

    # lista svih fajlova u bazi za dropdown
    file_names = VehicleRecord.objects.values_list("file_name", flat=True).distinct().order_by("file_name")

    return render(request, "app/ifta_list.html", {
        "page_obj": page_obj,
        "search": search,
        "total_count": total_count,
        "file_names": file_names,
        "file_filter": file_filter,
        "total_miles_sum": totals['total_miles_sum'] or 0,
        "total_fuel_sum": totals['total_fuel_sum'] or 0,
        "hide_header_and_footer": False
    })


@login_required
def vehicle_mpg(request):
    search = request.GET.get("search", "").strip()
    file_filter = request.GET.get("file_name", "all")
    export = request.GET.get("export")  # ako postoji export=1 u URL-u

    qs = VehicleRecord.objects.all()

    if search:
        qs = qs.filter(vehicle__icontains=search)

    if file_filter != "all":
        qs = qs.filter(file_name=file_filter)

    # Grupisanje po vozilu
    vehicle_stats = list(qs.values('vehicle').annotate(
        total_miles=Sum('total_miles'),
        total_gallons=Sum('fuel_qty')
    ).order_by('-total_miles', '-total_gallons'))

    # Dodavanje MPG
    for v in vehicle_stats:
        if v['total_gallons'] and v['total_gallons'] > 0:
            v['mpg'] = v['total_miles'] / v['total_gallons']
        else:
            v['mpg'] = 0

    # --- Export u Excel ---
    if export == "1":
        df = pd.DataFrame(vehicle_stats)
        df = df[['vehicle', 'total_miles', 'total_gallons', 'mpg']]  # redosled kolona
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename=vehicle_mpg.xlsx'
        with pd.ExcelWriter(response, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='MPG')
        return response

    # --- Render stranice ---
    return render(request, "app/mpg.html", {
        "vehicle_stats": vehicle_stats,
        "search": search,
        "file_filter": file_filter,
        "hide_header_and_footer": False
    })


@login_required
def vehicle_pivot_report(request):
    # agregacija po vehicle i jurisdiction
    qs = VehicleRecord.objects.values('vehicle', 'jurisdiction') \
        .annotate(
            total_miles_sum=Sum('total_miles'),
            fuel_qty_sum=Sum('fuel_qty')
        )

    if not qs.exists():
        return render(request, 'app/pivot_report.html', {
            'pivot': None,
            'jurisdiction_codes': None,
            'totals_per_vehicle': None,
            'totals_per_jurisdiction': None,
            "hide_header_and_footer": False
        })

    df = pd.DataFrame(list(qs))

    # pivot tabele
    pivot_miles = df.pivot(index='vehicle', columns='jurisdiction', values='total_miles_sum').fillna(0)
    pivot_fuel = df.pivot(index='vehicle', columns='jurisdiction', values='fuel_qty_sum').fillna(0)

    # dict sa tuple (miles, fuel)
    pivot_dict = {}
    for vehicle in pivot_miles.index:
        pivot_dict[vehicle] = {}
        for jurisdiction in pivot_miles.columns:
            miles = pivot_miles.at[vehicle, jurisdiction]
            fuel = pivot_fuel.at[vehicle, jurisdiction]
            pivot_dict[vehicle][jurisdiction] = (miles, fuel)

    # ukupno po vozacu
    totals_per_vehicle = {}
    for vehicle in pivot_miles.index:
        total_miles = pivot_miles.loc[vehicle].sum()
        total_fuel = pivot_fuel.loc[vehicle].sum()
        totals_per_vehicle[vehicle] = (total_miles, total_fuel)

    # ukupno po državi/jurisdikciji
    jurisdiction_codes = list(pivot_miles.columns)
    totals_per_jurisdiction = {}
    for jurisdiction in jurisdiction_codes:
        total_miles = sum(pivot_dict[v].get(jurisdiction, (0, 0))[0] for v in pivot_dict.keys())
        total_fuel = sum(pivot_dict[v].get(jurisdiction, (0, 0))[1] for v in pivot_dict.keys())
        totals_per_jurisdiction[jurisdiction] = (total_miles, total_fuel)

    return render(request, 'app/pivot_report.html', {
        'pivot': pivot_dict,
        'jurisdiction_codes': jurisdiction_codes,
        'totals_per_vehicle': totals_per_vehicle,
        'totals_per_jurisdiction': totals_per_jurisdiction,
        "hide_header_and_footer": False
    })


@login_required
def import_miles_files(request):
    if request.method == "POST":
        form = CombinedUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # --- 1. Učitaj i spoji sve miles fajlove ---
            miles_files = request.FILES.getlist("single_file")
            df_miles_all = pd.DataFrame()
            for f in miles_files:
                df = pd.read_excel(f)
                expected_cols_miles = ['Vehicle', 'Jurisdiction', 'Total Miles']
                if not all(col in df.columns for col in expected_cols_miles):
                    continue  # preskoči fajl ako nema kolone
                df = df[expected_cols_miles].copy()
                df['Vehicle'] = df['Vehicle'].astype(str).str.strip()
                df['Jurisdiction'] = df['Jurisdiction'].astype(str).str.strip()
                df['Total Miles'] = pd.to_numeric(df['Total Miles'], errors='coerce').fillna(0)
                df["file_name"] = f.name

                df_miles_all = pd.concat([df_miles_all, df], ignore_index=True)

            if df_miles_all.empty:
                return render(request, "app/upload.html", {"form": form, "error": "No valid miles data found.", "hide_header_and_footer": False})

            # Grupisanje po (vehicle, jurisdiction)
            df_miles_grouped = df_miles_all.groupby(
                ['Vehicle', 'Jurisdiction'],
                as_index=False
            ).agg({
                'Total Miles': 'sum',
                'file_name': 'first'  # jer je Vehicle uvek jedinstven po fajlovima
            })

            # --- 2. Učitaj i spoji sve fuel fajlove ---
            fuel_files = request.FILES.getlist("multiple_files")
            df_fuel_all = pd.DataFrame()
            for f in fuel_files:
                df = pd.read_excel(f)
                expected_cols_fuel = ['Unit', 'State', 'Qty']
                if not all(col in df.columns for col in expected_cols_fuel):
                    continue
                df = df[expected_cols_fuel].copy()
                df['Unit'] = df['Unit'].astype(str).str.strip()
                df['State'] = df['State'].astype(str).str.strip().str.upper()
                df['Qty'] = pd.to_numeric(df['Qty'], errors='coerce').fillna(0)
                df_fuel_all = pd.concat([df_fuel_all, df], ignore_index=True)

            # Grupisanje po (Unit, State)
            if not df_fuel_all.empty:
                df_fuel_grouped = df_fuel_all.groupby(['Unit', 'State'], as_index=False)['Qty'].sum()
            else:
                df_fuel_grouped = pd.DataFrame(columns=['Unit', 'State', 'Qty'])

            # --- 3. Merge miles + fuel ---
            df_miles_grouped.rename(columns={'Vehicle': 'vehicle', 'Jurisdiction': 'jurisdiction', 'Total Miles': 'total_miles', 'file_name': 'file_name'}, inplace=True)
            df_fuel_grouped.rename(columns={'Unit': 'vehicle', 'State': 'jurisdiction', 'Qty': 'fuel_qty'}, inplace=True)

            df_combined = pd.merge(df_miles_grouped, df_fuel_grouped, on=['vehicle', 'jurisdiction'], how='left')
            df_combined['fuel_qty'] = df_combined['fuel_qty'].fillna(0)

            # --- 4. Bulk insert / update ---
            # Napravi dict sa postojećim zapisima iz baze
            keys = list(zip(df_combined['vehicle'], df_combined['jurisdiction']))
            existing_records = VehicleRecord.objects.filter(
                vehicle__in=df_combined['vehicle'].unique(),
                jurisdiction__in=df_combined['jurisdiction'].unique()
            )
            existing_dict = {(r.vehicle, r.jurisdiction): r for r in existing_records}

            records_to_create = []
            records_to_update = []

            for _, row in df_combined.iterrows():
                key = (row['vehicle'], row['jurisdiction'])
                if key in existing_dict:
                    obj = existing_dict[key]
                    obj.total_miles = row['total_miles']
                    obj.fuel_qty = row['fuel_qty']
                    obj.file_name = row['file_name']
                    records_to_update.append(obj)
                else:
                    records_to_create.append(
                        VehicleRecord(
                            vehicle=row['vehicle'],
                            jurisdiction=row['jurisdiction'],
                            total_miles=row['total_miles'],
                            fuel_qty=row['fuel_qty'],
                            file_name=row['file_name']
                        )
                    )

            with transaction.atomic():
                if records_to_create:
                    VehicleRecord.objects.bulk_create(records_to_create, batch_size=1000)
                if records_to_update:
                    VehicleRecord.objects.bulk_update(records_to_update, ['total_miles', 'fuel_qty', 'file_name'], batch_size=1000)

            # --- 5. Optional: quarter i year ---
            quarter = form.cleaned_data.get("quarter")
            year = form.cleaned_data.get("year")

            return redirect("upload")  # ili neka stranica gde prikazuješ rezultate
        else:
            print(form.errors)
    else:
        form = CombinedUploadForm()

    return render(request, "app/upload.html", {"form": form, "hide_header_and_footer": False})


@login_required
def export_ifta(request):
    file_name = request.GET.get("file_name", "all")
    export_type = request.GET.get("type", "miles")  # miles ili fuel

    qs = VehicleRecord.objects.all()
    if file_name != "all":
        qs = qs.filter(file_name=file_name)

    if export_type == "miles":
        columns = ["vehicle", "jurisdiction", "total_miles"]
    else:  # fuel
        columns = ["vehicle", "jurisdiction", "fuel_qty"]

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{export_type}_{file_name}.csv"'

    writer = csv.writer(response)
    writer.writerow(columns)  # header

    for r in qs:
        writer.writerow([getattr(r, c) for c in columns])

    return response


@login_required
def export_ifta_excel(request):
    file_name = request.GET.get("file_name", "all")

    qs = VehicleRecord.objects.all()
    if file_name != "all":
        qs = qs.filter(file_name=file_name)

    # --- priprema DataFrame-ova ---
    df_miles = pd.DataFrame(list(qs.values("vehicle", "jurisdiction", "total_miles")))
    df_fuel  = pd.DataFrame(list(qs.values("vehicle", "jurisdiction", "fuel_qty")))

    # --- priprema response-a ---
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="IFTA_{file_name}.xlsx"'

    # --- kreiranje Excel fajla sa 2 sheet-a ---
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df_miles.to_excel(writer, index=False, sheet_name='Miles')
        df_fuel.to_excel(writer, index=False, sheet_name='Fuel')

    return response


@login_required
def fuel_efficiency_chart(request):
    vehicle_count = 60
    stats = (
        VehicleRecord.objects.values('vehicle')
        .annotate(
            sum_miles=Sum('total_miles'),
            sum_gallons=Sum('fuel_qty'),
        )
        .annotate(
            mpg=F('sum_miles') / F('sum_gallons')
        )
        .filter(sum_gallons__gt=0)
        .order_by('-mpg')
    )[:vehicle_count]

    data = [
        {
            "vehicle": s["vehicle"],
            "miles": round(s["sum_miles"], 2),
            "gallons": round(s["sum_gallons"], 2),
            "mpg": round(s["mpg"], 2),
        }
        for s in stats
    ]

    return render(request, "app/fuel_chart.html", {"data": data, "vehicle_count": vehicle_count, "hide_header_and_footer": False})


@login_required
def signout(request):
    logout(request)
    return redirect('/')


@xframe_options_sameorigin
def statistic(request):
    context = {"hide_header_and_footer": True}
    return render(request, "statistics/sample_table.html", context)


@xframe_options_sameorigin
def statistic2(request):
    rows = ActiveTrucksFinalGross.objects.all()
    context = {"rows": rows, "hide_header_and_footer": True}

    return render(request, "statistics/sample_table2.html", context)


def tv_rotator(request):
    return render(request, "statistics/tv_rotator.html", {"hide_header_and_footer": True})