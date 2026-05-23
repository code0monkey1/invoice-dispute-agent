import { Document, Page, View, Text, Image, Link, StyleSheet } from '@react-pdf/renderer';
import type { InvoiceData } from '../../../types';
import { computeTotals } from './shared/computeTotals';
import { formatCurrency } from './shared/formatCurrency';
import { formatDate } from './shared/formatDate';

interface Props { data: InvoiceData }

const DEFAULT_ACCENT = '#FF6B35';

const styles = StyleSheet.create({
  page: { paddingTop: 0, paddingBottom: 40, paddingHorizontal: 40, fontFamily: 'Helvetica', fontSize: 10 },
  band: { height: 40, marginBottom: 24 },
  header: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 24 },
  bizBlock: { flexDirection: 'column', maxWidth: 280 },
  bizName: { fontSize: 14, fontWeight: 'bold', marginBottom: 4 },
  bizAddr: { fontSize: 9, color: '#555', lineHeight: 1.4 },
  invMeta: { textAlign: 'right' },
  invLabel: { fontSize: 9, color: '#888', letterSpacing: 1 },
  invNum: { fontSize: 22, fontWeight: 'bold', marginTop: 2 },
  invDates: { fontSize: 9, color: '#555', marginTop: 6, lineHeight: 1.4 },
  section: { marginBottom: 16 },
  sectionLabel: { fontSize: 9, color: '#888', letterSpacing: 1, marginBottom: 4 },
  clientName: { fontSize: 11, fontWeight: 'bold' },
  clientLine: { fontSize: 9, color: '#444', lineHeight: 1.4 },
  table: { marginTop: 8 },
  thead: { flexDirection: 'row', borderBottomWidth: 1, paddingBottom: 4 },
  th: { fontSize: 9, color: '#888', fontWeight: 'bold' },
  tr: { flexDirection: 'row', paddingVertical: 4 },
  trAlt: { backgroundColor: '#FFF4EE' },
  td: { fontSize: 10 },
  col_desc: { flex: 4 },
  col_qty: { flex: 1, textAlign: 'right' },
  col_unit: { flex: 1.5, textAlign: 'right' },
  col_total: { flex: 1.5, textAlign: 'right' },
  totals: { marginTop: 12, alignItems: 'flex-end' },
  totalRow: { flexDirection: 'row', marginBottom: 2 },
  totalLabel: { width: 100, textAlign: 'right', marginRight: 12, color: '#666' },
  totalVal: { width: 80, textAlign: 'right' },
  totalGrand: { fontSize: 14, fontWeight: 'bold', marginTop: 4 },
  payBtn: {
    marginTop: 24,
    paddingVertical: 10,
    paddingHorizontal: 16,
    borderRadius: 6,
    color: '#FFFFFF',
    textAlign: 'center',
    textDecoration: 'none',
    fontWeight: 'bold',
    fontSize: 11,
    letterSpacing: 1,
  },
  payInstructions: { marginTop: 8, fontSize: 9, color: '#444', lineHeight: 1.4 },
  notes: { marginTop: 24, fontSize: 9, color: '#444', lineHeight: 1.4 },
  logo: { width: 60, height: 60, objectFit: 'contain', marginBottom: 8 },
});

export function ModernTemplate({ data }: Props) {
  const accent = data.accent_color || DEFAULT_ACCENT;
  const totals = computeTotals(data);
  const ccy = data.meta.currency;

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <View style={[styles.band, { backgroundColor: accent }]} />

        <View style={styles.header}>
          <View style={styles.bizBlock}>
            {data.sender.logo_url ? <Image style={styles.logo} src={data.sender.logo_url} /> : null}
            <Text style={styles.bizName}>{data.sender.business_name}</Text>
            <Text style={styles.bizAddr}>{data.sender.your_name}</Text>
            {data.sender.address ? <Text style={styles.bizAddr}>{data.sender.address}</Text> : null}
            <Text style={styles.bizAddr}>{data.sender.your_email}</Text>
            {data.sender.tax_id ? <Text style={styles.bizAddr}>Tax ID: {data.sender.tax_id}</Text> : null}
          </View>
          <View style={styles.invMeta}>
            <Text style={styles.invLabel}>INVOICE</Text>
            <Text style={styles.invNum}>{data.meta.invoice_number}</Text>
            <Text style={styles.invDates}>Issued: {formatDate(data.meta.issue_date)}</Text>
            <Text style={styles.invDates}>Due: {formatDate(data.meta.due_date)}</Text>
          </View>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionLabel}>BILL TO</Text>
          <Text style={styles.clientName}>{data.client.name}</Text>
          <Text style={styles.clientLine}>{data.client.email}</Text>
          {data.client.address ? <Text style={styles.clientLine}>{data.client.address}</Text> : null}
        </View>

        <View style={styles.table}>
          <View style={styles.thead}>
            <Text style={[styles.th, styles.col_desc]}>DESCRIPTION</Text>
            <Text style={[styles.th, styles.col_qty]}>QTY</Text>
            <Text style={[styles.th, styles.col_unit]}>UNIT</Text>
            <Text style={[styles.th, styles.col_total]}>TOTAL</Text>
          </View>
          {data.line_items.map((li, i) => (
            <View key={i} style={[styles.tr, i % 2 === 1 ? styles.trAlt : {}]}>
              <Text style={[styles.td, styles.col_desc]}>{li.description}</Text>
              <Text style={[styles.td, styles.col_qty]}>{li.quantity}</Text>
              <Text style={[styles.td, styles.col_unit]}>{formatCurrency(li.unit_price_cents, ccy)}</Text>
              <Text style={[styles.td, styles.col_total]}>
                {formatCurrency(Math.round(li.quantity * li.unit_price_cents), ccy)}
              </Text>
            </View>
          ))}
        </View>

        <View style={styles.totals}>
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
            <Text style={[styles.totalLabel, styles.totalGrand]}>Total</Text>
            <Text style={[styles.totalVal, styles.totalGrand]}>{formatCurrency(totals.total_cents, ccy)}</Text>
          </View>
        </View>

        {data.payment?.url ? (
          <Link src={data.payment.url} style={[styles.payBtn, { backgroundColor: accent }]}>
            {data.payment.label || 'PAY INVOICE →'}
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
