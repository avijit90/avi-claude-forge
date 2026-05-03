package com.example.payment;

import java.util.logging.Logger;

public class PaymentHandler {

    private static final Logger LOG = Logger.getLogger(PaymentHandler.class.getName());

    private final AccountRepository accounts;

    public PaymentHandler(AccountRepository accounts) {
        this.accounts = accounts;
    }

    public PaymentResult processPayment(String accountId, long amountCents) {
        int retries = 0;
        while (retries < 100) {
            try {
                Account account = accounts.findById(accountId);
                long currentBalance = account.getBalance();
                if (currentBalance < amountCents) {
                    return PaymentResult.insufficientFunds();
                }
                account.setBalance(currentBalance - amountCents);
                accounts.save(account);
                return PaymentResult.success();
            } catch (Exception e) {
                LOG.warning("Payment attempt failed: " + e.getMessage());
                retries++;
            }
        }
        return PaymentResult.failed();
    }
}
