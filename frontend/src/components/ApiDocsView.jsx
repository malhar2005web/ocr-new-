import React, { useState } from 'react';
import { Copy, Check, Terminal, Code2, Send, Sparkles } from 'lucide-react';
import { copyTextToClipboard } from '../services/clipboard';

export default function ApiDocsView() {
  const [copiedKey, setCopiedKey] = useState(null);

  const copyCode = async (key, text) => {
    const success = await copyTextToClipboard(text);
    if (success) {
      setCopiedKey(key);
      setTimeout(() => setCopiedKey(null), 2000);
    }
  };

  const pbPostmanUrl = `${window.location.origin}/api/v1/purchase-books/76`;
  const pbCurlExample = `curl -X GET "${window.location.origin}/api/v1/purchase-books/76"`;
  const pbSampleResponse = `{
  "Purchase Books": {
    "GRN No.": "",
    "Voucher No": "MT/1520",
    "Voucher Date  :": "14-Dec-21",
    "Supplier": "Mahaprabhuji Textiles",
    "Bill No": "MT/1520",
    "Bill Date  ": "14-Dec-21",
    "Product Amount": 243472.5,
    "Taxable Amount": 243472.5,
    "Total Qty": 10821.0,
    "Total Pcs": 115,
    "total Tax": 12173.62,
    "Invoice Amount": 255646.0,
    "Narration": "Indian Rupees Two Lakh Fifty Five Thousand Six Hundred Forty Six Only",
    "Product Details": [
      {
        "SrNo": 1,
        "Product": "Rudraksh 52*50-47 BALE[7} BALE NO 394 TO 400 PCS{115}",
        "Qty": 10821.0,
        "Rate": 22.5,
        "Value": 243472.5,
        "Pcs": 115,
        "Quality": "Rudraksh 52*50-47",
        "Other Information": "BALE NO 394 TO 400",
        "Location": "DYANE SHIWAR. MALEGAON, DIST. NASHIK, M.S.",
        "Remark": "BALE[7}",
        "Chapter Heading": "5208"
      }
    ],
    "Terms": "1) Interest @18% will be payable for the late payment from the due date.",
    "cgst": 6086.81,
    "sgst": 6086.81
  }
}`;

  const uPostmanUrl = `${window.location.origin}/api/v1/universal/76`;
  const uCurlExample = `curl -X GET "${window.location.origin}/api/v1/universal/76"`;
  const uSampleResponse = `{
  "buyer": {
    "name": "M.Tarun & Co",
    "gstin": "27AAHFM9152A1ZE",
    "state": "Maharashtra",
    "address": "413-F BASANTWADI 2ND FLOOR ROOM NO.31 KALBADEVI ROAD MUM-03",
    "state_code": "27"
  },
  "seller": {
    "name": "Mahaprabhuji Textiles",
    "gstin": "27AITPD0799E1ZY",
    "state": "Maharashtra",
    "address": "S.No. 26, P.No.25/26/31/32, Dayne Shiwar, Malegaon",
    "state_code": "27"
  },
  "consignee": {
    "name": "PAWAN PROCESS",
    "state": "Maharashtra",
    "address": "DYANE SHIWAR. MALEGAON, DIST. NASHIK, M.S.",
    "state_code": "27"
  },
  "line_items": [
    {
      "rate": "22.50",
      "unit": "Mtr",
      "sl_no": "1",
      "amount": "2,43,472.50",
      "pieces": "115",
      "quantity": "10821.00",
      "product_name": "Rudraksh 52*50-47 BALE[7} BALE NO 394 TO 400 PCS{115}"
    }
  ],
  "invoice_date": "14-Dec-21",
  "invoice_number": "MT/1520",
  "total_payable_amount": "255646.00"
}`;

  return (
    <div className="animate-fade-in" style={{ maxWidth: 980, margin: '0 auto' }}>
      <div style={{ marginBottom: 28 }}>
        <h1 className="page-title">Postman REST API Reference</h1>
        <p className="page-desc">
          Direct GET endpoints to retrieve extracted document JSON into Postman or ERP systems using SR NO or Document ID.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
        {/* API 1: Purchase Books ERP */}
        <div className="card" style={{ border: '1px solid var(--tiffany-border)', boxShadow: '0 4px 20px rgba(78, 205, 196, 0.08)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span 
                style={{ 
                  padding: '6px 14px', 
                  borderRadius: 6, 
                  fontWeight: 700, 
                  fontSize: '0.88rem',
                  background: 'rgba(16, 185, 129, 0.2)',
                  color: 'var(--success)',
                  fontFamily: 'var(--font-mono)'
                }}
              >
                GET
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-main)' }}>
                /api/v1/purchase-books/{'{id}'}
              </span>
            </div>
            <span style={{ fontSize: '0.8rem', padding: '4px 10px', borderRadius: 20, background: 'var(--tiffany-tint)', color: 'var(--tiffany-deep)', fontWeight: 600 }}>
              Purchase Books ERP JSON
            </span>
          </div>

          <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem', marginBottom: 18, lineHeight: 1.6 }}>
            Pass the document's <strong>SR NO</strong> (e.g. <code>76</code>, <code>77</code>) from the Dashboard / Explorer table, or the unique Document UUID. Returns the exact <strong>Purchase Books</strong> ERP JSON directly with exact accounting fields and spacing.
          </p>

          {/* Postman URL Quick Copy */}
          <div style={{ marginBottom: 18, padding: 14, background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Send size={14} color="var(--primary)" /> Postman Request URL
              </span>
              <button 
                className="btn btn-secondary" 
                style={{ padding: '4px 10px', fontSize: '0.78rem' }}
                onClick={() => copyCode('pb_postman', pbPostmanUrl)}
              >
                {copiedKey === 'pb_postman' ? <Check size={13} color="var(--success)" /> : <Copy size={13} />} Copy URL
              </button>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.88rem', color: 'var(--primary)', wordBreak: 'break-all' }}>
              {pbPostmanUrl}
            </div>
          </div>

          {/* cURL Example */}
          <div style={{ marginBottom: 18 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
                <Terminal size={14} /> cURL Request
              </span>
              <button 
                className="btn btn-secondary" 
                style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                onClick={() => copyCode('pb_curl', pbCurlExample)}
              >
                {copiedKey === 'pb_curl' ? <Check size={12} color="var(--success)" /> : <Copy size={12} />} Copy cURL
              </button>
            </div>
            <div className="code-block" style={{ fontSize: '0.82rem' }}>
              {pbCurlExample}
            </div>
          </div>

          {/* Sample Response */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
                <Code2 size={14} /> Result in Postman (Purchase Books ERP JSON)
              </span>
              <button 
                className="btn btn-secondary" 
                style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                onClick={() => copyCode('pb_resp', pbSampleResponse)}
              >
                {copiedKey === 'pb_resp' ? <Check size={12} color="var(--success)" /> : <Copy size={12} />} Copy JSON
              </button>
            </div>
            <div className="code-block" style={{ fontSize: '0.8rem', maxHeight: 220, overflowY: 'auto' }}>
              {pbSampleResponse}
            </div>
          </div>
        </div>

        {/* API 2: Universal JSON */}
        <div className="card" style={{ border: '1px solid var(--border-subtle)', boxShadow: '0 4px 20px rgba(15, 23, 42, 0.08)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <span 
                style={{ 
                  padding: '6px 14px', 
                  borderRadius: 6, 
                  fontWeight: 700, 
                  fontSize: '0.88rem',
                  background: 'rgba(99, 102, 241, 0.2)',
                  color: 'var(--primary)',
                  fontFamily: 'var(--font-mono)'
                }}
              >
                GET
              </span>
              <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-main)' }}>
                /api/v1/universal/{'{id}'}
              </span>
            </div>
            <span style={{ fontSize: '0.8rem', padding: '4px 10px', borderRadius: 20, background: 'rgba(99, 102, 241, 0.15)', color: 'var(--primary)', fontWeight: 600 }}>
              Universal Normalized JSON
            </span>
          </div>

          <p style={{ color: 'var(--text-muted)', fontSize: '0.92rem', marginBottom: 18, lineHeight: 1.6 }}>
            Pass the document's <strong>SR NO</strong> (e.g. <code>76</code>, <code>77</code>) from the Dashboard / Explorer table, or the unique Document UUID. Returns the complete <strong>Universal JSON</strong> with all normalized fields (buyer, seller, consignee, line items, taxes, and bank details).
          </p>

          {/* Postman URL Quick Copy */}
          <div style={{ marginBottom: 18, padding: 14, background: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <Send size={14} color="var(--primary)" /> Postman Request URL
              </span>
              <button 
                className="btn btn-secondary" 
                style={{ padding: '4px 10px', fontSize: '0.78rem' }}
                onClick={() => copyCode('u_postman', uPostmanUrl)}
              >
                {copiedKey === 'u_postman' ? <Check size={13} color="var(--success)" /> : <Copy size={13} />} Copy URL
              </button>
            </div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.88rem', color: 'var(--primary)', wordBreak: 'break-all' }}>
              {uPostmanUrl}
            </div>
          </div>

          {/* cURL Example */}
          <div style={{ marginBottom: 18 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
                <Terminal size={14} /> cURL Request
              </span>
              <button 
                className="btn btn-secondary" 
                style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                onClick={() => copyCode('u_curl', uCurlExample)}
              >
                {copiedKey === 'u_curl' ? <Check size={12} color="var(--success)" /> : <Copy size={12} />} Copy cURL
              </button>
            </div>
            <div className="code-block" style={{ fontSize: '0.82rem' }}>
              {uCurlExample}
            </div>
          </div>

          {/* Sample Response */}
          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-dim)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
                <Code2 size={14} /> Result in Postman (Universal Normalized JSON)
              </span>
              <button 
                className="btn btn-secondary" 
                style={{ padding: '4px 8px', fontSize: '0.75rem' }}
                onClick={() => copyCode('u_resp', uSampleResponse)}
              >
                {copiedKey === 'u_resp' ? <Check size={12} color="var(--success)" /> : <Copy size={12} />} Copy JSON
              </button>
            </div>
            <div className="code-block" style={{ fontSize: '0.8rem', maxHeight: 220, overflowY: 'auto' }}>
              {uSampleResponse}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
