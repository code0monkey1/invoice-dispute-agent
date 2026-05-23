import { Document, Page, View, Text, Image, Link, StyleSheet } from '@react-pdf/renderer';
import type { InvoiceData } from '../../../types';
import { computeTotals } from './shared/computeTotals';
import { formatCurrency } from './shared/formatCurrency';
import { formatDate } from './shared/formatDate';

interface Props { data: InvoiceData }

const styles = StyleSheet.create({
  page: { padding: 50, fontFamily: 'Times-Roman', fontSize: 10, color: '#000' },
  letterhead: { textAlign: 'center', marginBottom: 32 },
  bizName: { fontSize: 16, fontWeight: 'bold', letterSpacing: 2, marginBottom: 4 },
  bizLine: { fontSize: 9, lineHeight: 1.4 },
  rule: { borderBottomWidth: 1, marginVertical: 16 },
  metaRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 24 },
  metaLeft: { flexDirection: 'column' },
  metaLabel: { fontSize: 9, letterSpacing: 1, marginBottom: 4 },
  invNum: { fontSize: 18, fontWeight: 'bold' },
  metaRight: { textAlign: 'right' },
  table: { borderWidth: 1, marginBottom: 12 },
  thead: { flexDirection: 'row', borderBottomWidth: 1, padding: 6, backgroundColor: '#F5F5F0' },
  tr: { flexDirection: 'row', padding: 6, borderBottomWidth: 0.5, borderColor: '#999' },
  th: { fontSize: 9, fontWeight: 'bold', letterSpacing: 1 },
  td: { fontSize: 10 },
  col_desc: { flex: 4 },
  col_qty: { flex: 1, textAlign: 'right' },
  col_unit: { flex: 1.5, textAlign: 'right' },
  col_total: { flex: 1.5, textAlign: 'right' },
  totalsBox: {
    marginLeft: 'auto',
    width: 220,
    borderTopWidth: 2,
    borderBottomWidth: 2,
    paddingVertical: 8,
    marginTop: 8,
  },
  totalRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 2 },
  totalLabel: { fontSize: 10 },
  totalVal: { fontSize: 10 },
  grandLabel: { fontSize: 12, fontWeight: 'bold', marginTop: 4 },
  grandVal: { fontSize: 12, fontWeight: 'bold', marginTop: 4 },
  payBlock: { marginTop: 24 },
  payText: { fontSize: 10 },
  payLink: { color: '#1A4FBF', textDecoration: 'underline' },
  payInstructions: { marginTop: 8, fontSize: 9, lineHeight: 1.4 },
  notes: { marginTop: 24, fontSize: 9, lineHeight: 1.4 },
  logo: { width: 50, height: 50, alignSelf: 'center', marginBottom: 8 },
});

export function ClassicTemplate({ data }: Props) {
  const totals = computeTotals(data);
  const ccy = data.meta.currency;

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <View style={styles.letterhead}>
          {data.sender.logo_url ? <Image style={styles.logo} src={data.sender.logo_url} /> : null}
          <Text style={styles.bizName}>{data.sender.business_name?.toUpperCase()}</Text>
          {data.sender.address ? <Text style={styles.bizLine}>{data.sender.address}</Text> : null}
          <Text style={styles.bizLine}>{data.sender.your_email}</Text>
          {data.sender.tax_id ? <Text style={styles.bizLine}>Tax ID: {data.sender.tax_id}</Text> : null}
        </View>

        <View style={styles.rule} />

        <View style={styles.metaRow}>
          <View style={styles.metaLeft}>
            <Text style={styles.metaLabel}>BILL TO</Text>
            <Text style={[styles.td, { fontWeight: 'bold' }]}>{data.client.name}</Text>
            <Text style={styles.bizLine}>{data.client.email}</Text>
            {data.client.address ? <Text style={styles.bizLine}>{data.client.address}</Text> : null}
          </View>
          <View style={styles.metaRight}>
            <Text style={styles.metaLabel}>INVOICE</Text>
            <Text style={styles.invNum}>{data.meta.invoice_number}</Text>
            <Text style={styles.bizLine}>Issued: {formatDate(data.meta.issue_date)}</Text>
            <Text style={styles.bizLine}>Due: {formatDate(data.meta.due_date)}</Text>
          </View>
        </View>

        <View style={styles.table}>
          <View style={styles.thead}>
            <Text style={[styles.th, styles.col_desc]}>DESCRIPTION</Text>
            <Text style={[styles.th, styles.col_qty]}>QTY</Text>
            <Text style={[styles.th, styles.col_unit]}>UNIT</Text>
            <Text style={[styles.th, styles.col_total]}>TOTAL</Text>
          </View>
          {data.line_items.map((li, i) => (
            <View key={i} style={styles.tr}>
              <Text style={[styles.td, styles.col_desc]}>{li.description}</Text>
              <Text style={[styles.td, styles.col_qty]}>{li.quantity}</Text>
              <Text style={[styles.td, styles.col_unit]}>{formatCurrency(li.unit_price_cents, ccy)}</Text>
              <Text style={[styles.td, styles.col_total]}>
                {formatCurrency(Math.round(li.quantity * li.unit_price_cents), ccy)}
              </Text>
            </View>
          ))}
        </View>

        <View style={styles.totalsBox}>
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
          <View style={styles.payBlock}>
            <Text style={styles.payText}>
              Pay online:{' '}
              <Link src={data.payment.url} style={styles.payLink}>{data.payment.url}</Link>
            </Text>
          </View>
        ) : null}

        {data.payment_instructions ? (
          <Text style={styles.payInstructions}>{data.payment_instructions}</Text>
        ) : null}

        {data.notes ? <Text style={styles.notes}>{data.notes}</Text> : null}
      </Page>
    </Document>
  );
}
