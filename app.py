import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(page_title="Eshop Dashboard", layout="wide")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

menu = st.sidebar.radio("Menu", ["Ver pedidos", "Insertar pedido", "Reportes"])


def cargar_pedidos():
    response = supabase.table("Order").select(
        "Id, OrderDate, Customer(Customer, Email), OrderLine(Quantity, UnitPrice, Product(Title))"
    ).execute()
    filas = []
    for pedido in response.data:
        cliente = pedido["Customer"]["Customer"] if pedido["Customer"] else "N/A"
        for linea in pedido["OrderLine"]:
            filas.append({
                "OrderId": pedido["Id"],
                "Fecha": pedido["OrderDate"],
                "Cliente": cliente,
                "Producto": linea["Product"]["Title"] if linea["Product"] else "N/A",
                "Cantidad": linea["Quantity"],
                "PrecioUnitario": linea["UnitPrice"],
                "Subtotal": linea["Quantity"] * linea["UnitPrice"],
            })
    return pd.DataFrame(filas)


if menu == "Ver pedidos":
    st.title("Pedidos")
    df = cargar_pedidos()
    if df.empty:
        st.info("Todavia no hay pedidos registrados")
    else:
        st.dataframe(df, use_container_width=True)
        st.metric("Total facturado", f"S/ {df['Subtotal'].sum():,.2f}")

elif menu == "Insertar pedido":
    st.title("Nuevo pedido")

    clientes = supabase.table("Customer").select("Id, Customer").execute().data
    productos = supabase.table("Product").select("Id, Title, UnitPrice").execute().data

    if not clientes or not productos:
        st.warning("Necesitas tener al menos un cliente y un producto creados en Supabase")
    else:
        cliente_map = {c["Customer"]: c["Id"] for c in clientes}
        producto_map = {p["Title"]: p for p in productos}

        cliente_sel = st.selectbox("Cliente", list(cliente_map.keys()))

        if "lineas" not in st.session_state:
            st.session_state.lineas = []

        col1, col2, col3 = st.columns(3)
        with col1:
            producto_sel = st.selectbox("Producto", list(producto_map.keys()))
        with col2:
            cantidad = st.number_input("Cantidad", min_value=1, value=1)
        with col3:
            st.write("")
            st.write("")
            if st.button("Agregar producto al pedido"):
                p = producto_map[producto_sel]
                st.session_state.lineas.append({
                    "ProductId": p["Id"],
                    "Producto": producto_sel,
                    "Quantity": cantidad,
                    "UnitPrice": p["UnitPrice"],
                })

        if st.session_state.lineas:
            st.write("Productos en este pedido:")
            st.table(pd.DataFrame(st.session_state.lineas)[["Producto", "Quantity", "UnitPrice"]])

            if st.button("Confirmar y guardar pedido", type="primary"):
                customer_id = cliente_map[cliente_sel]

                nuevo_pedido = supabase.table("Order").insert({
                    "CustomerId": customer_id
                }).execute()
                order_id = nuevo_pedido.data[0]["Id"]

                for linea in st.session_state.lineas:
                    supabase.table("OrderLine").insert({
                        "OrderId": order_id,
                        "ProductId": linea["ProductId"],
                        "Quantity": linea["Quantity"],
                        "UnitPrice": linea["UnitPrice"],
                    }).execute()

                st.success(f"Pedido {order_id} guardado correctamente")
                st.session_state.lineas = []
                st.rerun()

elif menu == "Reportes":
    st.title("Reportes")
    df = cargar_pedidos()
    if df.empty:
        st.info("Todavia no hay data para reportes")
    else:
        st.subheader("Total gastado por cliente")
        resumen_cliente = df.groupby("Cliente")["Subtotal"].sum().sort_values(ascending=False)
        st.bar_chart(resumen_cliente)

        st.subheader("Productos mas vendidos")
        resumen_producto = df.groupby("Producto")["Cantidad"].sum().sort_values(ascending=False)
        st.bar_chart(resumen_producto)
