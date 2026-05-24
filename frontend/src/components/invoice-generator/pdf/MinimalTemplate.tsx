import { Document, Page, View, Text, Link, StyleSheet } from '@react-pdf/renderer';
import type { InvoiceData } from '../../../types';
import { computeTotals } from './shared/computeTotals';
import { formatCurrency } from './shared/formatCurrency';
import { formatDate } from './shared/formatDate';

interface Props { data: InvoiceData }

const styles = StyleSheet.create({
  page: { paddingTop: 72, paddingBottom: 72, paddingHorizontal: 64, fontFamily: 'Helvetica', fontSize: 10, color: '#000' },
  caption: { fontSize: 9, color: '#888', letterSpacing: 2, marginBottom: 4 },
  invNum: { fontSize: 28, marginBottom: 32 },
  pair: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 24 },
  block: { flexDirection: 'column', flexShrink: 1 },
  label: { fontSize: 8, color: '#888', letterSpacing: 1, marginBottom: 2 },
  textLine: { fontSize: 10, lineHeight: 1.4 },
  itemsHeader: { flexDirection: 'row', marginTop: 24, paddingBottom: 4 },
  hLabel: { fontSize: 8, color: '#888', letterSpacing: 1 },
  itemRow: { flexDirection: 'row', paddingVertical: 6 },
  col_desc: { flex: 4 },
  col_qty: { flex: 1, textAlign: 'right' },
  col_total: { flex: 2, textAlign: 'right' },
  ruleTop: { borderTopWidth: 1, marginTop: 8, paddingTop: 8 },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 2 },
  totalLabel: { fontSize: 10 },
  totalVal: { fontSize: 10 },
  grandLabel: { fontSize: 12, fontWeight: 'bold', marginTop: 8 },
  grandVal: { fontSize: 12, fontWeight: 'bold', marginTop: 8 },
  payLink: { marginTop: 40, fontSize: 11, textDecoration: 'underline', color: '#000' },
  payInstructions: { marginTop: 8, fontSize: 9, lineHeight: 1.4 },
  notes: { marginTop: 32, fontSize: 9, lineHeight: 1.4 },
});

export function MinimalTemplate({ data }: Props) {
  const totals = computeTotals(data);
  const ccy = data.meta.currency;

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <Text style={styles.caption}>INVOICE</Text>
        <Text style={styles.invNum}>{data.meta.invoice_number}</Text>

        <View style={styles.pair}>
          <View style={styles.block}>
            <Text style={styles.label}>FROM</Text>
            <Text style={[styles.textLine, { fontWeight: 'bold' }]}>{data.sender.business_name}</Text>
            <Text style={styles.textLine}>{data.sender.your_name}</Text>
            <Text style={styles.textLine}>{data.sender.your_email}</Text>
            {data.sender.address ? <Text style={styles.textLine}>{data.sender.address}</Text> : null}
            {data.sender.tax_id ? <Text style={styles.textLine}>Tax ID: {data.sender.tax_id}</Text> : null}
          </View>
          <View style={styles.block}>
            <Text style={styles.label}>BILL TO</Text>
            <Text style={[styles.textLine, { fontWeight: 'bold' }]}>{data.client.name}</Text>
            <Text style={styles.textLine}>{data.client.email}</Text>
            {data.client.address ? <Text style={styles.textLine}>{data.client.address}</Text> : null}
          </View>
          <View style={styles.block}>
            <Text style={styles.label}>DATES</Text>
            <Text style={styles.textLine}>Issued {formatDate(data.meta.issue_date)}</Text>
            <Text style={styles.textLine}>Due {formatDate(data.meta.due_date)}</Text>
          </View>
        </View>

        <View style={styles.itemsHeader}>
          <Text style={[styles.hLabel, styles.col_desc]}>DESCRIPTION</Text>
          <Text style={[styles.hLabel, styles.col_qty]}>QTY × UNIT</Text>
          <Text style={[styles.hLabel, styles.col_total]}>AMOUNT</Text>
        </View>
        {data.line_items.map((li, i) => (
          <View key={i} style={styles.itemRow}>
            <Text style={[styles.textLine, styles.col_desc]}>{li.description}</Text>
            <Text style={[styles.textLine, styles.col_qty]}>
              {li.quantity} × {formatCurrency(li.unit_price_cents, ccy)}
            </Text>
            <Text style={[styles.textLine, styles.col_total]}>
              {formatCurrency(Math.round(li.quantity * li.unit_price_cents), ccy)}
            </Text>
          </View>
        ))}

        <View style={styles.ruleTop}>
          <View style={styles.totalRow}>
            <Text style={styles.totalLabel}>Subtotal</Text>
            <Text style={styles.totalVal}>{formatCurrency(totals.subtotal_cents, ccy)}</Text>
          </View>
          {totals.discount_cents > 0 ? (
            <View style={styles.totalRow}>
              <Text style={styles.totalLabel}>Discount</Text>
              <Text style={styles.totalVal}>− {formatCurrency(totals.discount_cents, ccy)}</Text>
            </View>
          ) : null}
          {totals.tax_cents > 0 ? (
            <View style={styles.totalRow}>
              <Text style={styles.totalLabel}>Tax ({data.tax_rate_pct ?? 0}%)</Text>
              <Text style={styles.totalVal}>{formatCurrency(totals.tax_cents, ccy)}</Text>
            </View>
          ) : null}
          <View style={styles.totalRow}>
            <Text style={styles.grandLabel}>Total</Text>
            <Text style={styles.grandVal}>{formatCurrency(totals.total_cents, ccy)}</Text>
          </View>
        </View>

        {data.payment?.url ? (
          <Link src={data.payment.url} style={styles.payLink}>
            {data.payment.label || 'Pay this invoice →'}
          </Link>
        ) : null}

        {data.payment_instructions ? (
          <Text style={styles.payInstructions}>{data.payment_instructions}</Text>
        ) : null}

        {data.notes ? <Text style={styles.notes}>{data.notes}</Text> : null}
      </Page>
    </Document>
  );
}
