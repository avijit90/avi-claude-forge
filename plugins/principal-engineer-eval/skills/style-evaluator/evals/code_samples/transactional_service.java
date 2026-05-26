package com.example.billing;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Isolation;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.transaction.support.TransactionSynchronizationManager;

import java.math.BigDecimal;
import java.util.List;

/**
 * Sample service exercising several transaction-management patterns.
 * Used by the style-evaluator's `evidence` category — the eval expects the
 * model to identify each transaction boundary, propagation choice, and
 * whether nested calls participate in or open new transactions.
 */
@Service
public class BillingService {

    @Autowired private InvoiceRepository invoiceRepo;
    @Autowired private LedgerRepository ledgerRepo;
    @Autowired private AuditLogService auditLogService;
    @Autowired private NotificationService notificationService;

    /**
     * Default propagation: REQUIRED. Joins an existing transaction if present,
     * otherwise opens a new one. Read-only flag hints the JDBC driver to skip
     * write-related setup.
     */
    @Transactional(readOnly = true)
    public Invoice findInvoice(long invoiceId) {
        return invoiceRepo.findById(invoiceId)
                .orElseThrow(() -> new InvoiceNotFoundException(invoiceId));
    }

    /**
     * REQUIRES_NEW: suspends any caller's transaction and starts a fresh one.
     * Used here so audit log writes survive even if the caller's transaction
     * later rolls back.
     */
    @Transactional(propagation = Propagation.REQUIRES_NEW)
    public void recordAudit(String actor, String action, long invoiceId) {
        auditLogService.write(actor, action, invoiceId);
    }

    /**
     * REQUIRED + SERIALIZABLE: full ACID for ledger writes. Lock contention
     * possible under concurrent posts to the same account.
     */
    @Transactional(isolation = Isolation.SERIALIZABLE, rollbackFor = Exception.class)
    public Invoice postPayment(long invoiceId, BigDecimal amount) throws PaymentException {
        Invoice invoice = invoiceRepo.findByIdForUpdate(invoiceId)
                .orElseThrow(() -> new InvoiceNotFoundException(invoiceId));

        if (invoice.isClosed()) {
            throw new PaymentException("invoice " + invoiceId + " is closed");
        }

        ledgerRepo.appendEntry(invoice.getAccountId(), amount.negate());
        invoice.applyPayment(amount);
        invoiceRepo.save(invoice);

        // Nested call. recordAudit's REQUIRES_NEW will suspend this transaction
        // and commit the audit row independently.
        recordAudit("system", "PAYMENT_POSTED", invoiceId);

        // Self-invocation issue: notifyCustomer is in this same bean, so the
        // @Transactional on it is BYPASSED — Spring's proxy isn't invoked here.
        notifyCustomer(invoice);

        return invoice;
    }

    /**
     * SUPPORTS: participates in a transaction if one exists, otherwise runs
     * non-transactionally. The notify call doesn't strictly need a tx.
     */
    @Transactional(propagation = Propagation.SUPPORTS)
    public void notifyCustomer(Invoice invoice) {
        notificationService.send(invoice.getCustomerId(),
                "Payment posted: " + invoice.getId());
    }

    /**
     * NOT_SUPPORTED: any caller transaction is suspended. Use this for slow
     * external calls that should not hold DB locks.
     */
    @Transactional(propagation = Propagation.NOT_SUPPORTED)
    public List<ExternalCharge> fetchUpstreamCharges(long invoiceId) {
        return notificationService.getUpstreamCharges(invoiceId);
    }

    /**
     * NESTED: SAVEPOINT inside the caller's transaction. If reconcile() throws
     * a runtime exception, only the savepoint rolls back — the outer tx can
     * continue to commit other work. Requires a JDBC driver supporting
     * savepoints.
     */
    @Transactional(propagation = Propagation.NESTED)
    public void reconcile(long invoiceId) {
        Invoice invoice = invoiceRepo.findById(invoiceId).orElseThrow();
        List<LedgerEntry> entries = ledgerRepo.findByAccountId(invoice.getAccountId());
        BigDecimal balance = entries.stream()
                .map(LedgerEntry::getAmount)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        invoice.setReconciledBalance(balance);
        invoiceRepo.save(invoice);
    }

    /**
     * MANDATORY: must be called inside an existing transaction; otherwise
     * Spring throws IllegalTransactionStateException.
     */
    @Transactional(propagation = Propagation.MANDATORY)
    public void appendLedgerEntry(long accountId, BigDecimal amount) {
        if (!TransactionSynchronizationManager.isActualTransactionActive()) {
            // unreachable in normal flow — MANDATORY would have thrown already
            throw new IllegalStateException("expected active transaction");
        }
        ledgerRepo.appendEntry(accountId, amount);
    }

    /**
     * No @Transactional. This method is non-transactional. Each repo call
     * runs in its own auto-commit. Listed here intentionally — the eval
     * expects the model to flag this as a boundary worth calling out.
     */
    public InvoiceSummary buildSummary(long invoiceId) {
        Invoice invoice = invoiceRepo.findById(invoiceId).orElseThrow();
        List<LedgerEntry> entries = ledgerRepo.findByAccountId(invoice.getAccountId());
        return new InvoiceSummary(invoice, entries);
    }
}
