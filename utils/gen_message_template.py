def gen_transaction_receipt(
    customer_name: str,
    transaction_id: str,
    shop_name: str,
    total_price: float,
    items: list,
    receipt_url: str,
    payment_mode: str | None = None,
) -> str:
    short_id = transaction_id[-8:].upper()
    item_lines = "\n".join(
        f"  {item['product_name']} x{item['quantity']}"
        f" = GHS {item['subtotal']:.2f}"
        for item in items
    )
    payment_line = f"Payment: {payment_mode.upper()}\n" if payment_mode else ""
    return (
        f"{shop_name}\n"
        f"Receipt #{short_id}\n"
        f"{item_lines}\n"
        f"Total: GHS {total_price:.2f}\n"
        f"{payment_line}"
        f"Thank you, {customer_name}!\n"
        f"View receipt: {receipt_url}"
    )


def gen_refund_notice(
    customer_name: str,
    transaction_id: str,
    shop_name: str,
    total_price: float,
    receipt_url: str,
) -> str:
    short_id = transaction_id[-8:].upper()
    return (
        f"{shop_name}\n"
        f"Your purchase (Receipt #{short_id}) of GHS {total_price:.2f} has "
        f"been refunded, {customer_name}.\n"
        f"View receipt: {receipt_url}"
    )
