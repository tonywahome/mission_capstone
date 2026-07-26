import Link from "next/link";
import Image from "next/image";

export const metadata = {
  title: "Privacy Policy — TerraFoma",
};

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-terra-50 to-green-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto space-y-8">
        <div className="text-center">
          <div className="flex justify-center">
            <Image src="/logo.png" alt="TerraFoma" width={100} height={100} className="object-contain" />
          </div>
          <h1 className="mt-4 text-3xl font-bold text-gray-900">
            TerraFoma Prototype — Privacy Policy
          </h1>
          <p className="mt-2 text-sm text-gray-600">
            African Leadership University — BSc. Software Engineering Capstone Project
          </p>
          <p className="text-sm text-gray-500">
            Prepared by Wahome A. Wambugu · Supervisor: Mr. Emmanuel Adjei
          </p>
          <p className="text-xs text-gray-400 mt-1">Effective date: 26 July 2026 · Version 1.0</p>
        </div>

        <div className="bg-white rounded-2xl shadow-lg p-8 space-y-8 text-sm leading-relaxed text-gray-700">
          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-gray-900">1. Scope and Purpose</h2>
            <p>
              This Privacy Policy applies to the TerraFoma prototype (&ldquo;the Prototype&rdquo; or &ldquo;the
              Dashboard&rdquo;), a research artefact developed by Wahome A. Wambugu as part of a BSc. Software
              Engineering capstone at the African Leadership University (ALU), Kigali, Rwanda, under the supervision
              of Mr. Emmanuel Adjei. The Prototype is a locally calibrated machine-learning system and lightweight
              web dashboard for above-ground biomass (AGB) estimation, project registration, field-data upload, and
              result visualisation, developed and validated with a purposive sample of stakeholder groups in the
              Bugesera and Rulindo districts of Rwanda, as described in the accompanying capstone report.
            </p>
            <p>
              This is a <strong>proof-of-concept academic prototype</strong>, not a commercial product. It is
              distinct from any commercial entity operating under a similar name in Rwanda; nothing in this Policy
              extends to, or should be read as describing, the data practices of any such commercial venture. This
              Policy exists to document, transparently and in writing, how the Prototype is designed to collect,
              use, protect, and retain personal and geospatial data gathered during the capstone&apos;s
              stakeholder-interview and field-validation phases, consistent with the ethical and data-protection
              commitments set out in the capstone report.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-gray-900">2. Data Controller</h2>
            <p>
              <strong>Data Controller:</strong> Wahome A. Wambugu, in his capacity as researcher for this capstone
              project, acting under the academic supervision of the ALU Faculty of Software Engineering.
            </p>
            <p>
              <strong>Contact:</strong> a.wambugu@alustudent.com
            </p>
            <p>
              <strong>Academic Supervisor:</strong> Mr. Emmanuel Adjei, Faculty of Software Engineering, African
              Leadership University.
            </p>
            <p>
              Questions, requests to exercise data-subject rights, or complaints regarding this Prototype&apos;s
              handling of personal data should be directed to the contact above in the first instance.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-gray-900">3. Categories of Data Collected</h2>

            <h3 className="font-semibold text-gray-800">3.1 Stakeholder Interview Data</h3>
            <p>
              Collected from land-steward and cooperative representatives, agricultural extension officers,
              representatives of the Rwanda Environment Management Authority (REMA) and the Rwanda Forestry
              Authority (RFA), project developers, and carbon-credit buyers/intermediaries interviewed for
              requirements gathering:
            </p>
            <ul className="list-disc list-inside space-y-1">
              <li>Name and role/affiliation</li>
              <li>Contact information (phone number and/or email address)</li>
              <li>Interview responses, including views on measurement, cost, tenure, and market-access barriers</li>
            </ul>

            <h3 className="font-semibold text-gray-800">3.2 Field Reference and Geospatial Data</h3>
            <p>
              Collected during field-plot validation across the two land-cover strata (agroforestry and
              grassland/savanna):
            </p>
            <ul className="list-disc list-inside space-y-1">
              <li>Precise GPS coordinates of plot corners</li>
              <li>Tree diameter at breast height (DBH), height, and species composition per plot</li>
              <li>Association between a plot and the land steward or cooperative registering it</li>
            </ul>

            <h3 className="font-semibold text-gray-800">3.3 Dashboard Account and Usage Data</h3>
            <p>
              Collected from users of the prototype web dashboard (land stewards, verifiers/analysts, and research
              administrators):
            </p>
            <ul className="list-disc list-inside space-y-1">
              <li>Account identifiers and role assignment (steward, verifier/analyst, or research administrator)</li>
              <li>Registered project and parcel records associated with an account</li>
              <li>Uploaded field data and system-generated biomass/carbon-stock estimates and audit-trail logs</li>
            </ul>

            <h3 className="font-semibold text-gray-800">3.4 Data Not Collected</h3>
            <p>
              The Prototype does not collect financial account details, government identity numbers, biometric
              data, or health data. It does not process data relating to minors; all interviewees and registering
              stewards are adults participating in a professional or livelihood capacity.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-gray-900">4. Legal Basis and Consent</h2>
            <p>
              Personal data is processed on the basis of the data subject&apos;s freely given, informed consent,
              obtained prior to any interview or field-data collection. Consent is sought using plain-language
              explanations delivered in Kinyarwanda and adapted to local norms of consent, recognising that
              standardised written-consent procedures can be inappropriate in rural settings and may require
              community-level engagement alongside individual agreement. Participation is voluntary, and any
              participant may withdraw consent and request cessation of further processing at any time without
              penalty.
            </p>
            <p>
              <strong>Separate consent for location data.</strong> Consent to be interviewed, or for aggregate
              biomass data to be used in the study, is obtained separately from consent to store precise GPS parcel
              coordinates. A participant may decline the storage of precise location data while continuing to
              participate in other respects.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-gray-900">5. How Data Is Used</h2>
            <p>Data collected through the Prototype is used solely for the following capstone research purposes:</p>
            <ul className="list-disc list-inside space-y-1">
              <li>Calibrating and validating the locally trained machine-learning biomass-estimation model</li>
              <li>
                Generating wall-to-wall biomass and carbon-stock maps with quantified uncertainty for the study
                area
              </li>
              <li>Populating the project-registration, field-data-upload, and result-visualisation functions of the dashboard</li>
              <li>
                Producing an auditable record (audit trail) of how a given biomass estimate was derived, for expert
                review of dMRV traceability
              </li>
              <li>Academic analysis, reporting, and evaluation of the capstone&apos;s stated objectives</li>
            </ul>
            <p>
              Data is not used for commercial purposes, sold, or disclosed to advertisers or unrelated third
              parties, and is not used for any carbon-credit issuance, buyer-matching, or settlement activity, which
              are explicitly outside the Prototype&apos;s scope.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-gray-900">6. Data Sharing and Disclosure</h2>
            <p>Personal and geospatial data collected under this Policy is shared only in the following limited circumstances:</p>
            <ul className="list-disc list-inside space-y-1">
              <li>With the academic supervisor and, where required, ALU examiners, for the purposes of assessing the capstone</li>
              <li>
                With cloud-processing services (Google Earth Engine, for satellite-imagery composite generation) —
                no personal or field-plot identifying data is transmitted to these services, which process only
                satellite raster imagery
              </li>
              <li>
                Where required by law or by REMA/RFA institutional-access arrangements described in the capstone
                report&apos;s stakeholder-recruitment plan, and only to the extent necessary
              </li>
            </ul>
            <p>
              The Prototype does not share data with data brokers, advertisers, or any party for marketing
              purposes. No cross-border transfer of identifying personal data occurs outside the systems described
              above.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-gray-900">7. Data Protection Safeguards</h2>

            <h3 className="font-semibold text-gray-800">7.1 Coordinate Rounding</h3>
            <p>
              Precise GPS plot coordinates are retained at full precision only within the secure, access-controlled
              research database used for model training. Any coordinates appearing in reports, the dashboard&apos;s
              visualisation layer, or academic write-ups are rounded to a precision no finer than approximately 100
              metres — sufficient for district- and stratum-level reporting but insufficient to identify an
              individual farmer&apos;s exact plot boundary.
            </p>

            <h3 className="font-semibold text-gray-800">7.2 Role-Based Access Control</h3>
            <p>The dashboard implements three access roles:</p>
            <ul className="list-disc list-inside space-y-1">
              <li>Land steward — may view and edit only their own registered plots</li>
              <li>Verifier/analyst — may view plot-level data within their assigned district for audit purposes</li>
              <li>Research administrator — the only role with access to the full, unrounded dataset</li>
            </ul>
            <p>No non-administrative user can view identifying data outside their own legitimate scope.</p>

            <h3 className="font-semibold text-gray-800">7.3 Technical Security Measures</h3>
            <p>
              Consistent with the system architecture described in the capstone report, the Prototype applies
              authentication controls, a PostgreSQL/PostGIS data layer with restricted access, and containerised
              (Docker) deployment to support a consistent security configuration across environments. As a research
              prototype, these controls are appropriate to an academic proof-of-concept and are not represented as
              production-grade security certification.
            </p>

            <h3 className="font-semibold text-gray-800">7.4 Data Minimisation</h3>
            <p>
              Only data necessary to calibrate and validate the biomass-estimation model, and to operate the
              registration/visualisation dashboard, is collected. Identifying information is stored separately from
              de-identified research/analysis data wherever technically practicable.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-gray-900">8. Data Retention</h2>
            <p>
              <strong>Identifying data</strong> (names, contact details, and unrounded GPS coordinates) is retained
              only for the duration of the capstone project and a subsequent twelve-month period, to allow for
              academic review and potential publication, after which it is securely deleted.
            </p>
            <p>
              <strong>Rounded, de-identified data</strong> (aggregate biomass and land-cover data) may be retained
              for longer to support potential future research, consistent with the consent obtained from
              participants.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-gray-900">9. Data Subject Rights</h2>
            <p>
              Any participant whose data is processed under this Policy may, subject to the practical limits of an
              academic research context, request to:
            </p>
            <ul className="list-disc list-inside space-y-1">
              <li>Access the personal data held about them</li>
              <li>Correct inaccurate data</li>
              <li>Withdraw consent and request deletion of their data, including withdrawal from the study</li>
              <li>Ask questions about how their data has been or will be used</li>
            </ul>
            <p>
              Requests may be directed to the contact in Section 2. Rwandan data subjects also retain the rights
              and remedies available to them under Law N° 058/2021 of 13/10/2021 Relating to the Protection of
              Personal Data and Privacy, including the ability to lodge a complaint with Rwanda&apos;s National
              Cyber Security Authority / Data Protection and Privacy Office.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-gray-900">10. Governing Law</h2>
            <p>
              This Prototype&apos;s data-handling practices are designed to be consistent with Law N° 058/2021 of
              13/10/2021 Relating to the Protection of Personal Data and Privacy (Rwanda), and with the
              research-ethics standards for information and communication technology for development (ICT4D) work,
              which emphasise respect, reciprocity, and the avoidance of extractive practice. Institutional ethical
              clearance is obtained prior to any fieldwork.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-gray-900">11. Limitations of This Policy</h2>
            <p>
              This document describes the data practices of a capstone research prototype and proof-of-concept,
              evaluated against the criteria set out in the accompanying capstone report. It does not constitute,
              and should not be relied upon as, a commercial privacy policy, a data-processing agreement, or a
              warranty of production-grade data security. Biomass and carbon-stock estimates produced by the
              Prototype carry quantified uncertainty and should not be treated as certified or audited
              carbon-accounting outputs.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-gray-900">12. Changes to This Policy</h2>
            <p>
              This Policy may be updated to reflect changes in the Prototype&apos;s design or in applicable law.
              The effective date at the top of this document indicates the version currently in force. Material
              changes affecting previously collected data will be communicated to affected participants where
              reasonably practicable.
            </p>
          </section>

          <section className="space-y-3">
            <h2 className="text-lg font-semibold text-gray-900">13. Contact</h2>
            <p>
              <strong>Researcher:</strong> Wahome A. Wambugu — a.wambugu@alustudent.com
              <br />
              <strong>Institution:</strong> African Leadership University, Kigali, Rwanda
              <br />
              <strong>Supervisor:</strong> Mr. Emmanuel Adjei, Faculty of Software Engineering
            </p>
          </section>
        </div>

        <div className="text-center">
          <Link href="/signup" className="font-semibold text-terra-600 hover:text-terra-700 text-sm">
            &larr; Back to sign up
          </Link>
        </div>
      </div>
    </div>
  );
}
